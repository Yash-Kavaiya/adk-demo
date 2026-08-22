"""MediaAcquisitionAgent: download, transcript and curated frames per video."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from bookforge.config import get_settings
from bookforge.schemas import MediaBundle, VideoRecord
from bookforge.tools import frames as frame_tools
from bookforge.tools import youtube as yt
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)


class MediaAcquisitionAgent(BaseAgent):
    """Stage 2 (per video): local download + transcript + deduped frames.

    Transcript strategy: human/auto captions first (free, timestamp-aligned);
    faster-whisper on the extracted audio as fallback. Everything is
    idempotent — re-running a stage reuses existing files.
    """

    name: str = "media_acquisition"
    description: str = (
        "Downloads the video at capped resolution, obtains a timestamped "
        "transcript (captions or whisper), extracts frames every N seconds "
        "and removes duplicates via perceptual hashing."
    )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        settings = get_settings()
        state = ctx.session.state
        record = VideoRecord.model_validate(state["current_video"])
        ws = Workspace(settings.workspace_root_abs, state["channel_slug"])
        vdir = ws.video_dir(record.video_id)

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
        ws.update_video(record.video_id, status="media", error="")

        transcript_text = yt.load_transcript_text(transcript_path)
        if not transcript_text.strip():
            raise RuntimeError(f"empty transcript for {record.video_id}")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"Media ready for '{record.title}': transcript via "
                        f"{source} ({len(transcript_text)} chars), "
                        f"{len(deduped)}/{len(raw_frames)} unique frames."
                    )
                ],
            ),
            actions=EventActions(
                state_delta={
                    "transcript": transcript_text,
                    "transcript_source": source,
                    "frame_count": len(deduped),
                }
            ),
        )
