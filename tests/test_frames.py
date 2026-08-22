"""Frame dedupe + curation on synthetic images (no ffmpeg needed)."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFilter

from bookforge.tools.frames import curate_frames, dedupe_frames


def make_frame(path: Path, seed_text: str, color: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (160, 90), color)
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), seed_text, fill=(255, 255, 255))
    img.save(path, "JPEG")


def test_dedupe_collapses_static_runs(tmp_path):
    paths = []
    # 5 identical "slide" frames, then 3 of a different scene, then 1 blurred
    for i in range(5):
        p = tmp_path / f"frame_{i:05d}.jpg"
        make_frame(p, "SLIDE A", (20, 20, 120))
        paths.append(p)
    for i in range(5, 8):
        p = tmp_path / f"frame_{i:05d}.jpg"
        make_frame(p, "SCENE B with different content ######", (200, 30, 30))
        paths.append(p)
    blurry = tmp_path / "frame_00008.jpg"
    img = Image.new("RGB", (160, 90), (128, 128, 128)).filter(
        ImageFilter.GaussianBlur(12)
    )
    img.save(blurry, "JPEG")
    paths.append(blurry)

    kept = dedupe_frames(paths, interval_sec=5, hash_threshold=6)
    assert len(kept) == 2  # slide-run + scene-run; blur dropped
    assert kept[0].timestamp_sec == pytest.approx(2.5)
    assert kept[1].timestamp_sec == pytest.approx(27.5)


def test_curate_spreads_and_renames(tmp_path):
    src = tmp_path / "raw"
    src.mkdir()
    assets = []
    for i in range(20):
        p = src / f"frame_{i:05d}.jpg"
        make_frame(p, f"frame number {i}", (i * 12 % 255, 50, 200))
        assets.append(
            type("A", (), {"file": str(p), "timestamp_sec": i * 5.0, "phash": "x"})()
        )

    from bookforge.schemas import FrameAsset

    assets = [
        FrameAsset(file=a.file, timestamp_sec=a.timestamp_sec, phash=a.phash)
        for a in assets
    ]

    dest = tmp_path / "figures"
    curated = curate_frames(assets, src, dest, max_frames=6)
    assert len(curated) == 6
    names = [f.file for f in curated]
    assert names == sorted(names)  # ordered across timeline
    assert all((dest / n).exists() for n in names)  # actually copied
    assert all(n.startswith("frame_") and n.endswith("s.jpg") for n in names)
