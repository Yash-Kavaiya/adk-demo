"""Tests for parallel video processing with locking."""

import asyncio
from pathlib import Path

import pytest

from bookforge.schemas import VideoRecord
from bookforge.tools.workspace import Workspace
from bookforge.tools.workspace_lock import safe_update_video, get_workspace_lock


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    """Create a test workspace."""
    ws = Workspace(tmp_path, "test-channel")
    manifest = ws.init_manifest(
        "https://youtube.com/@test", "Test Channel", "test-channel"
    )
    
    # Add test videos
    for i in range(1, 6):
        manifest.videos.append(
            VideoRecord(
                video_id=f"video_{i}",
                title=f"Test Video {i}",
                url=f"https://youtu.be/video_{i}",
                duration_sec=300,
                chapter_number=i,
                status="pending",
            )
        )
    
    ws.save_manifest(manifest)
    return ws


def test_workspace_lock_creation(tmp_path):
    """Test that locks are created per workspace."""
    ws1 = Workspace(tmp_path / "ws1", "channel1")
    ws2 = Workspace(tmp_path / "ws2", "channel2")
    
    lock1 = get_workspace_lock(ws1.root)
    lock2 = get_workspace_lock(ws2.root)
    
    # Different workspaces should have different locks
    assert lock1 is not lock2
    
    # Same workspace should return same lock
    lock1_again = get_workspace_lock(ws1.root)
    assert lock1 is lock1_again


@pytest.mark.asyncio
async def test_safe_update_video_sequential(workspace):
    """Test safe update in sequential execution (baseline)."""
    # Update video 1
    manifest = await safe_update_video(workspace, "video_1", status="media")
    assert manifest.by_id("video_1").status == "media"
    
    # Update video 2
    manifest = await safe_update_video(workspace, "video_2", status="analyzed")
    assert manifest.by_id("video_2").status == "analyzed"
    
    # Verify both updates persisted
    manifest = workspace.load_manifest()
    assert manifest.by_id("video_1").status == "media"
    assert manifest.by_id("video_2").status == "analyzed"


@pytest.mark.asyncio
async def test_safe_update_video_concurrent(workspace):
    """Test that concurrent updates don't corrupt manifest."""
    
    async def update_video(video_id: str, status: str):
        """Simulate processing a video."""
        await asyncio.sleep(0.01)  # Simulate work
        await safe_update_video(workspace, video_id, status=status)
        await asyncio.sleep(0.01)  # Simulate more work
    
    # Update 5 videos concurrently
    tasks = [
        update_video("video_1", "media"),
        update_video("video_2", "analyzed"),
        update_video("video_3", "assets"),
        update_video("video_4", "written"),
        update_video("video_5", "verified"),
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify all updates succeeded
    manifest = workspace.load_manifest()
    assert manifest.by_id("video_1").status == "media"
    assert manifest.by_id("video_2").status == "analyzed"
    assert manifest.by_id("video_3").status == "assets"
    assert manifest.by_id("video_4").status == "written"
    assert manifest.by_id("video_5").status == "verified"


@pytest.mark.asyncio
async def test_concurrent_updates_same_video(workspace):
    """Test race condition prevention for same video.
    
    This simulates the scenario where two tasks try to update the same
    video (e.g., one sets it to 'media', another to 'failed'). The locking
    should ensure the last update wins consistently.
    """
    
    async def update_to_status(video_id: str, status: str, delay: float):
        """Update after a delay."""
        await asyncio.sleep(delay)
        await safe_update_video(workspace, video_id, status=status)
    
    # Both tasks try to update video_1
    # The second one (failed) should win because it runs last
    await asyncio.gather(
        update_to_status("video_1", "media", 0.01),
        update_to_status("video_1", "failed", 0.02),
    )
    
    manifest = workspace.load_manifest()
    # The last update should win
    assert manifest.by_id("video_1").status == "failed"


@pytest.mark.asyncio
async def test_many_concurrent_updates(workspace):
    """Stress test with many concurrent updates."""
    
    # Use valid status values from the enum
    statuses = ["pending", "media", "analyzed", "assets", "written", "verified", "failed"]
    
    async def update_many_times(video_id: str, count: int):
        """Update a video multiple times."""
        for i in range(count):
            status = statuses[i % len(statuses)]  # Cycle through valid statuses
            await safe_update_video(
                workspace, video_id, status=status, error=f"iter_{i}"
            )
            await asyncio.sleep(0.001)  # Small delay
    
    # Run 100 updates across 5 videos concurrently
    tasks = [update_many_times(f"video_{i}", 20) for i in range(1, 6)]
    await asyncio.gather(*tasks)
    
    # Verify manifest is not corrupted
    manifest = workspace.load_manifest()
    assert len(manifest.videos) == 5
    
    # Each video should have a valid status (last update in the cycle)
    for i in range(1, 6):
        record = manifest.by_id(f"video_{i}")
        assert record is not None
        # Last status should be from the cycle: statuses[19 % 7] = statuses[5] = "verified"
        assert record.status in statuses
        assert record.error == "iter_19"  # Last iteration


@pytest.mark.asyncio
async def test_error_handling_in_concurrent_updates(workspace):
    """Test that errors in one task don't break others."""
    
    async def update_with_error(video_id: str):
        """Simulate an update that fails."""
        try:
            await safe_update_video(workspace, video_id, status="media")
            if video_id == "video_3":
                raise ValueError("Simulated error")
        except ValueError:
            await safe_update_video(workspace, video_id, status="failed", error="test error")
    
    # Run updates, one will fail
    tasks = [
        update_with_error("video_1"),
        update_with_error("video_2"),
        update_with_error("video_3"),  # This one fails
        update_with_error("video_4"),
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify all updates succeeded (including the error case)
    manifest = workspace.load_manifest()
    assert manifest.by_id("video_1").status == "media"
    assert manifest.by_id("video_2").status == "media"
    assert manifest.by_id("video_3").status == "failed"
    assert manifest.by_id("video_3").error == "test error"
    assert manifest.by_id("video_4").status == "media"


def test_sequential_mode_still_works(workspace):
    """Test that sequential (non-async) updates still work."""
    # Direct workspace update (original method)
    workspace.update_video("video_1", status="media")
    
    manifest = workspace.load_manifest()
    assert manifest.by_id("video_1").status == "media"
