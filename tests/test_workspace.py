"""Workspace + manifest behaviour: roundtrip, status updates, resume listing."""

from pathlib import Path

from bookforge.schemas import VideoRecord
from bookforge.tools.workspace import Workspace, slugify


def make_ws(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path, "test-channel")


def test_slugify():
    assert slugify("My Channel! (2024)") == "my-channel-2024"
    assert slugify("###") == "untitled"


def test_manifest_roundtrip(tmp_path):
    ws = make_ws(tmp_path)
    manifest = ws.init_manifest("https://youtube.com/@x", "X Channel", "test-channel")
    manifest.videos.append(
        VideoRecord(
            video_id="abc",
            title="First",
            url="https://youtu.be/abc",
            duration_sec=600,
            chapter_number=1,
        )
    )
    ws.save_manifest(manifest)

    loaded = ws.load_manifest()
    assert loaded.channel_slug == "test-channel"
    assert loaded.videos[0].status == "pending"
    assert ws.pending_videos()[0].video_id == "abc"


def test_update_video_and_pending_filter(tmp_path):
    ws = make_ws(tmp_path)
    manifest = ws.init_manifest("u", "t", "test-channel")
    for i in range(1, 4):
        manifest.videos.append(
            VideoRecord(
                video_id=f"v{i}",
                title=f"T{i}",
                url=f"https://youtu.be/v{i}",
                chapter_number=i,
            )
        )
    ws.save_manifest(manifest)

    ws.update_video("v1", status="verified")
    ws.update_video("v2", status="failed", error="boom")

    pending_ids = [v.video_id for v in ws.pending_videos()]
    assert (
        pending_ids == ["v2", "v3"]
        or pending_ids == ["v3", "v2"]
        or "v1" not in pending_ids
    )
    assert "v1" not in pending_ids
    loaded = ws.load_manifest()
    record_v2 = loaded.by_id("v2")
    assert record_v2 is not None and record_v2.error == "boom"


def test_chapter_dir_layout(tmp_path):
    ws = make_ws(tmp_path)
    record = VideoRecord(
        video_id="v", title="Deep Dive: Transformers", url="u", chapter_number=3
    )
    chapter_dir = ws.chapter_dir(record)
    assert chapter_dir.name == "03_deep-dive-transformers"
    assert (chapter_dir / "figures").is_dir()
    assert (chapter_dir / "tables").is_dir()


def test_atomic_json_write(tmp_path):
    ws = make_ws(tmp_path)
    ws.init_manifest("u", "t", "test-channel")
    # second save must replace cleanly (no .tmp leftovers)
    ws.update_video  # noqa: B018 - attribute exists
    m = ws.load_manifest()
    m.channel_title = "renamed"
    ws.save_manifest(m)
    assert ws.load_manifest().channel_title == "renamed"
    assert not list(tmp_path.rglob("*.tmp"))
