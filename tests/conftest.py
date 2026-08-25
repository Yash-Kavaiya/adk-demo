"""Shared fixtures for BookForge tests."""

import os
from pathlib import Path

import pytest

from bookforge.config import Settings
from bookforge.schemas import VideoRecord
from bookforge.tools.workspace import Workspace

# Keep unit tests offline: importing bookforge.agent would otherwise try MLflow.
os.environ.setdefault("BOOKFORGE_DISABLE_MLFLOW_TRACING", "1")


@pytest.fixture
def settings() -> Settings:
    """Test-safe settings with compile_latex disabled."""
    return Settings(
        compile_latex=False,
        max_videos=1,
        workspace_root=Path("test_data"),
        analyst_model="gemini-2.5-flash",
        writer_model="gemini-2.5-flash",
        critic_model="gemini-2.5-flash",
    )


@pytest.fixture
def workspace(tmp_path) -> Workspace:
    """A fresh workspace in a temp directory."""
    ws = Workspace(tmp_path, "test-channel")
    manifest = ws.init_manifest(
        "https://youtube.com/@test", "Test Channel", "test-channel"
    )
    manifest.videos.append(
        VideoRecord(
            video_id="test123",
            title="Test Video",
            url="https://youtu.be/test123",
            duration_sec=300,
            chapter_number=1,
        )
    )
    ws.save_manifest(manifest)
    return ws


@pytest.fixture
def sample_video_record() -> VideoRecord:
    """A sample VideoRecord for testing."""
    return VideoRecord(
        video_id="abc123",
        title="Introduction to Machine Learning",
        url="https://www.youtube.com/watch?v=abc123",
        duration_sec=1200,
        upload_date="20240101",
        chapter_number=1,
        status="pending",
    )
