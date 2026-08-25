"""MediaAcquisitionAgent: download, transcript and curated frames per video."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from bookforge.config import get_settings
from bookforge.schemas import VideoRecord
from bookforge.tools.media_acquire import acquire_media_bundle
from bookforge.tools.workspace import Workspace
from bookforge.tools.workspace_lock import safe_update_video

logger = logging.getLogger(__name__)


class MediaAcquisitionAgent(BaseAgent):
    """Stage 2 (per video): local download + transcript + deduped frames.

    Transcript strategy: human/auto captions first (free, timestamp-aligned);
    faster-whisper on the extracted audio as fallback. Everything is
    idempotent — re-running a stage reuses existing files. Production can
    prefetch this work in a thread while another chapter is in the LLM stages.
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

        bundle, transcript_text = acquire_media_bundle(record, ws, settings)
        await safe_update_video(ws, record.video_id, status="media", error="")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"Media ready for '{record.title}': transcript via "
                        f"{bundle.transcript_source} ({len(transcript_text)} chars), "
                        f"{len(bundle.frames)} unique frames."
                    )
                ],
            ),
            actions=EventActions(
                state_delta={
                    "transcript": transcript_text,
                    "transcript_source": bundle.transcript_source,
                    "frame_count": len(bundle.frames),
                }
            ),
        )
