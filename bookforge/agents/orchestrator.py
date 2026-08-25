"""BookProductionAgent (resumable per-video loop) + root graph builder.

Media for upcoming chapters is prefetched in parallel (thread pool) while the
current chapter runs the LLM/QA stages. The ADK session graph itself stays
sequential so session state cannot be clobbered.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from bookforge.agents.analyst import make_analyst_agent
from bookforge.agents.assets import VisualAssetAgent
from bookforge.agents.compiler import BookCompilerAgent
from bookforge.agents.critic import make_qa_loop
from bookforge.agents.intake import ChannelIntakeAgent
from bookforge.agents.media import MediaAcquisitionAgent
from bookforge.agents.writer import make_writer_agent
from bookforge.config import Settings, get_settings
from bookforge.progress import ProgressTracker, format_duration
from bookforge.schemas import VideoRecord
from bookforge.tools import latex as latex_tools
from bookforge.tools.media_acquire import acquire_media_bundle
from bookforge.tools.workspace import Workspace
from bookforge.tools.workspace_lock import safe_update_video

logger = logging.getLogger(__name__)


def _text_event(author: str, text: str) -> Event:
    return Event(
        author=author,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


class BookProductionAgent(BaseAgent):
    """Runs chapter_pipeline once per pending video, with checkpointing.

    A video that raises is marked `failed` in the manifest and the loop
    continues — one broken video never blocks the book. Re-running the agent
    skips every video already `verified`.
    """

    name: str = "book_production"
    description: str = "Resumable loop: one book chapter per pending video."
    pipeline: SequentialAgent

    def __init__(self, pipeline: SequentialAgent, **kwargs) -> None:
        super().__init__(pipeline=pipeline, sub_agents=[pipeline], **kwargs)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        settings = get_settings()
        state = ctx.session.state
        ws = Workspace(settings.workspace_root_abs, state["channel_slug"])
        pending = ws.pending_videos()
        tracker = ProgressTracker(len(pending))
        prefetch_n = max(1, settings.media_prefetch_concurrency)

        yield _text_event(
            self.name,
            f"Producing {len(pending)} chapters. "
            f"Media prefetch x{prefetch_n} in parallel. "
            f"Initial ETA ~{format_duration(tracker.eta_sec())} "
            f"(~{format_duration(tracker.average_chapter_sec())}/chapter).",
        )

        prefetch_task = asyncio.create_task(
            self._prefetch_media(ws, pending[1:], prefetch_n)
        )
        try:
            async for event in self._run_sequential(ctx, ws, pending, tracker):
                yield event
        finally:
            if not prefetch_task.done():
                prefetch_task.cancel()
                try:
                    await prefetch_task
                except (asyncio.CancelledError, Exception):
                    pass

        yield _text_event(self.name, tracker.summary())
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"production_done": True}),
        )

    async def _prefetch_media(
        self, ws: Workspace, records: list[VideoRecord], concurrency: int
    ) -> None:
        if not records:
            return
        settings = get_settings()
        sem = asyncio.Semaphore(max(1, concurrency))

        async def one(record: VideoRecord) -> None:
            async with sem:
                try:
                    await asyncio.to_thread(
                        acquire_media_bundle, record, ws, settings
                    )
                    logger.info("prefetched media for %s", record.video_id)
                except Exception:
                    logger.exception("media prefetch failed for %s", record.video_id)

        await asyncio.gather(*(one(r) for r in records), return_exceptions=True)

    async def _run_sequential(
        self,
        ctx: InvocationContext,
        ws: Workspace,
        pending: list[VideoRecord],
        tracker: ProgressTracker,
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        for index, record in enumerate(pending):
            state["current_video"] = record.model_dump()
            state["video_id"] = record.video_id
            state["video_title"] = record.title
            state["qa_verdict"] = "unknown"
            state["chapter_tex"] = ""
            state["critique"] = ""

            yield _text_event(
                self.name,
                tracker.start_chapter(index, record.title),
            )

            try:
                async for event in self.pipeline.run_async(ctx):
                    yield event

                tex = latex_tools.sanitize_chapter_tex(state.get("chapter_tex", ""))
                if not tex.strip():
                    raise RuntimeError("pipeline produced an empty chapter")
                Workspace.write_text(ws.chapter_dir(record) / "chapter.tex", tex)

                verdict = state.get("qa_verdict", "unknown")
                status = "verified" if verdict == "pass" else "written"
                await safe_update_video(ws, record.video_id, status=status, error="")
                yield _text_event(
                    self.name,
                    tracker.finish_chapter(index, record.title, status),
                )
            except Exception as exc:
                logger.exception("chapter pipeline failed for %s", record.video_id)
                await safe_update_video(
                    ws, record.video_id, status="failed", error=str(exc)[:500]
                )
                yield _text_event(
                    self.name,
                    tracker.finish_chapter(index, record.title, "failed")
                    + f" Error: {exc}",
                )


def build_chapter_pipeline(settings: Settings) -> SequentialAgent:
    return SequentialAgent(
        name="chapter_pipeline",
        description="One video -> one verified book chapter.",
        sub_agents=[
            MediaAcquisitionAgent(),
            make_analyst_agent(settings),
            VisualAssetAgent(),
            make_writer_agent(settings),
            make_qa_loop(settings),
        ],
    )


def build_root_agent(settings: Settings | None = None) -> SequentialAgent:
    """The BookForge root agent (used by `adk run`, `adk web`, and the CLI)."""
    settings = settings or get_settings()
    return SequentialAgent(
        name="bookforge",
        description=(
            "Turns a YouTube channel URL into a compiled LaTeX book: "
            "intake -> per-video chapters (media, analysis, assets, writing, "
            "QA loop) -> final book compilation."
        ),
        sub_agents=[
            ChannelIntakeAgent(),
            BookProductionAgent(pipeline=build_chapter_pipeline(settings)),
            BookCompilerAgent(),
        ],
    )
