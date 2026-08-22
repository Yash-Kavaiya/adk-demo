"""ChannelIntakeAgent: YouTube channel URL -> resumable videos.json manifest."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from bookforge.config import get_settings
from bookforge.schemas import VideoRecord
from bookforge.tools.workspace import Workspace, slugify
from bookforge.tools.youtube import list_channel_videos

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s\"']*(?:youtube\.com|youtu\.be)[^\s\"']*")


def extract_channel_url(text: str) -> str | None:
    match = _URL_RE.search(text or "")
    if match:
        url = match.group(0)
        return re.sub(r"[.,;/\s]+$", "", url)
    return None


class ChannelIntakeAgent(BaseAgent):
    """Stage 1: resolve the channel, build (or resume) the video manifest."""

    name: str = "channel_intake"
    description: str = (
        "Fetches every video link of a YouTube channel into a versioned, "
        "resumable JSON manifest (one future chapter per video)."
    )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        settings = get_settings()
        state = ctx.session.state

        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            user_text = " ".join(p.text or "" for p in ctx.user_content.parts)
        channel_url = extract_channel_url(user_text) or state.get("channel_url")
        if not channel_url:
            raise ValueError(
                "No YouTube channel URL found in the user message or session state."
            )

        channel_title, videos = list_channel_videos(
            channel_url,
            max_videos=settings.max_videos,
            min_duration_sec=settings.min_video_duration_sec,
            max_duration_sec=settings.max_video_duration_sec,
        )
        if not videos:
            raise RuntimeError(f"No eligible videos found at {channel_url}")

        slug = slugify(channel_title)
        ws = Workspace(settings.workspace_root_abs, slug)

        if ws.manifest_exists():
            manifest = ws.load_manifest()
            logger.info("resuming existing manifest: %d videos", len(manifest.videos))
        else:
            manifest = ws.init_manifest(channel_url, channel_title, slug)
            # Chronological order -> the book reads like the channel evolved.
            videos.sort(key=lambda v: (v["upload_date"] == "", v["upload_date"]))
            for i, v in enumerate(videos, start=1):
                manifest.videos.append(VideoRecord(chapter_number=i, **v))
            ws.save_manifest(manifest)

        pending = ws.pending_videos()
        summary = {
            "channel_url": channel_url,
            "channel_slug": slug,
            "channel_title": manifest.channel_title or channel_title,
            "videos": [v.model_dump() for v in manifest.videos],
            "total_videos": len(manifest.videos),
            "pending_videos": len(pending),
        }
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"Intake complete: {len(manifest.videos)} videos "
                        f"({len(pending)} pending) from "
                        f"'{summary['channel_title']}'."
                    )
                ],
            ),
            actions=EventActions(state_delta=summary),
        )
