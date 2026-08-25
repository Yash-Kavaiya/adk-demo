"""Idempotent per-video media acquisition (download, transcript, frames).

Safe to call from a worker thread / prefetch task. Reuses existing files.
"""

from __future__ import annotations

import logging

from pathlib import Path

from bookforge.config import Settings
from bookforge.schemas import MediaBundle, VideoRecord
from bookforge.tools import frames as frame_tools
from bookforge.tools import youtube as yt
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)


def acquire_media_bundle(
    record: VideoRecord,
    ws: Workspace,
    settings: Settings,
) -> tuple[MediaBundle, str]:
    """Download + transcript + frames. Returns (bundle, transcript_text)."""
    vdir = ws.video_dir(record.video_id)
    existing = vdir / "media.json"
    if existing.exists():
        bundle = MediaBundle.model_validate_json(
            existing.read_text(encoding="utf-8")
        )
        transcript_text = yt.load_transcript_text(Path(bundle.transcript_path))
        if transcript_text.strip():
            return bundle, transcript_text

    video_path = yt.download_video(
        record.url, vdir, max_height=settings.download_resolution
    )

    captions = yt.fetch_captions(record.url, vdir)
    if captions is not None:
        transcript_path = yt.vtt_to_text(captions, vdir)
        source = "captions"
    else:
        logger.info("no captions for %s; falling back to whisper", record.video_id)
        audio_path = yt.extract_audio(video_path, vdir)
        transcript_path = yt.whisper_transcribe(
            audio_path, vdir, model_size=settings.whisper_model
        )
        source = "whisper"

    raw_frames = frame_tools.extract_frames(
        video_path, vdir / "frames_raw", settings.frame_interval_sec
    )
    deduped = frame_tools.dedupe_frames(
        raw_frames,
        interval_sec=settings.frame_interval_sec,
        hash_threshold=settings.frame_phash_threshold,
    )

    bundle = MediaBundle(
        video_id=record.video_id,
        video_path=str(video_path),
        transcript_path=str(transcript_path),
        transcript_source=source,  # type: ignore[arg-type]
        frames=deduped,
    )
    Workspace.write_text(vdir / "media.json", bundle.model_dump_json(indent=2))
    transcript_text = yt.load_transcript_text(Path(transcript_path))
    if not transcript_text.strip():
        raise RuntimeError(f"empty transcript for {record.video_id}")
    return bundle, transcript_text
