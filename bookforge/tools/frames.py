"""Frame extraction, dedupe and curation.

Pipeline per video:
    ffmpeg fps=1/interval -> frames_raw/
    -> perceptual-hash dedupe + blur/darkness rejection -> frames/
    -> spread curation (max K frames across the timeline)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import imagehash
from PIL import Image, ImageFilter, ImageStat

from bookforge.schemas import FrameAsset

logger = logging.getLogger(__name__)

_FRAME_GLOB = "frame_*.jpg"


def extract_frames(
    video_path: Path, out_dir: Path, interval_sec: int = 5
) -> list[Path]:
    """One screenshot every `interval_sec`; idempotent per directory."""
    out_dir = Path(out_dir)
    existing = sorted(out_dir.glob(_FRAME_GLOB))
    if existing:
        return existing
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "frame_%05d.jpg")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps=1/{max(1, interval_sec)}",
        "-q:v",
        "3",
        pattern,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {proc.stderr[-2000:]}")
    frames = sorted(out_dir.glob(_FRAME_GLOB))
    if not frames:
        raise RuntimeError(f"ffmpeg produced no frames for {video_path}")
    return frames


def _sharpness(img: Image.Image) -> float:
    """Cheap focus proxy: mean intensity of an edge-detected grayscale copy."""
    edges = img.convert("L").resize((64, 64)).filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(edges).mean[0])


def _brightness(img: Image.Image) -> float:
    return float(ImageStat.Stat(img.convert("L").resize((32, 32))).mean[0])


def _contrast(img: Image.Image) -> float:
    """Stddev of luminance: robust junk detector for flat/blurred frames."""
    return float(ImageStat.Stat(img.convert("L").resize((64, 64))).stddev[0])


def dedupe_frames(
    frame_paths: list[Path],
    interval_sec: int,
    hash_threshold: int = 6,
    min_sharpness: float = 4.0,
    min_contrast: float = 6.0,
    brightness_range: tuple[float, float] = (12.0, 245.0),
) -> list[FrameAsset]:
    """Drop near-duplicates (pHash hamming <= threshold) and junk frames.

    Frames are processed in order; a frame is kept only if it differs from the
    last KEPT frame — this collapses long static runs (slides, pauses) while
    keeping genuine visual changes.
    """
    kept: list[FrameAsset] = []
    last_hash: imagehash.ImageHash | None = None
    for index, path in enumerate(frame_paths):
        try:
            with Image.open(path) as img:
                img.load()
                sharp = _sharpness(img)
                bright = _brightness(img)
                contrast = _contrast(img)
                if (
                    sharp < min_sharpness
                    or contrast < min_contrast
                    or not (brightness_range[0] <= bright <= brightness_range[1])
                ):
                    continue
                current = imagehash.phash(img)
        except Exception as exc:  # noqa: BLE001 - corrupt frames come in many flavors
            logger.warning("skipping unreadable frame %s: %s", path, exc)
            continue
        if last_hash is not None and abs(current - last_hash) <= hash_threshold:
            continue
        last_hash = current
        timestamp = (index + 0.5) * interval_sec  # ffmpeg fps sampling offset
        kept.append(
            FrameAsset(
                file=str(path), timestamp_sec=round(timestamp, 1), phash=str(current)
            )
        )
    return kept


def curate_frames(
    assets: list[FrameAsset],
    src_dir: Path,
    dest_dir: Path,
    max_frames: int,
) -> list[FrameAsset]:
    """Keep at most `max_frames`, spread evenly across the video timeline.

    Selected frames are copied into `dest_dir` (the chapter figures source).
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if len(assets) > max_frames:
        step = len(assets) / max_frames
        picked = [assets[int(i * step)] for i in range(max_frames)]
    else:
        picked = list(assets)

    curated: list[FrameAsset] = []
    for i, asset in enumerate(picked, start=1):
        src = Path(asset.file)
        dest = dest_dir / f"frame_{i:02d}_{int(asset.timestamp_sec)}s.jpg"
        if not dest.exists():
            dest.write_bytes(src.read_bytes())
        curated.append(
            FrameAsset(
                file=dest.name, timestamp_sec=asset.timestamp_sec, phash=asset.phash
            )
        )
    return curated
