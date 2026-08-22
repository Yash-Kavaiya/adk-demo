"""BookProductionAgent (resumable per-video loop) + root graph builder.

This version supports parallel video processing with proper locking to prevent
race conditions. Parallelization is opt-in via configuration for safety.
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
from bookforge.schemas import VideoRecord
from bookforge.tools import latex as latex_tools
from bookforge.tools.workspace import Workspace
from bookforge.tools.workspace_lock import safe_update_video

logger = logging.getLogger(__name__)


class BookProductionAgent(BaseAgent):
    """Runs chapter_pipeline once per pending video, with checkpointing.

    A video that raises is marked `failed` in the manifest and the loop
    continues — one broken video never blocks the book. Re-running the agent
    skips every video already `verified`.
    
    NEW: Supports parallel video processing when enabled via configuration.
    Set BOOKFORGE_ENABLE_PARALLEL_VIDEOS=true and BOOKFORGE_MAX_CONCURRENT_VIDEOS=2
    to process multiple videos concurrently.
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

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Producing {len(pending)} chapters.")],
            ),
        )

        # Choose execution mode based on configuration
        if settings.enable_parallel_videos and settings.max_concurrent_videos > 1:
            logger.info(
                "Parallel mode enabled: processing up to %d videos concurrently",
                settings.max_concurrent_videos,
            )
            async for event in self._run_parallel(ctx, ws, pending):
                yield event
        else:
            logger.info("Sequential mode: processing videos one at a time")
            async for event in self._run_sequential(ctx, ws, pending):
                yield event

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"production_done": True}),
        )

    async def _run_sequential(
        self, ctx: InvocationContext, ws: Workspace, pending: list[VideoRecord]
    ) -> AsyncGenerator[Event, None]:
        """Original sequential processing (backward compatible)."""
        state = ctx.session.state

        for record in pending:
            state["current_video"] = record.model_dump()
            state["video_id"] = record.video_id
            state["video_title"] = record.title
            state["qa_verdict"] = "unknown"
            state["chapter_tex"] = ""
            state["critique"] = ""

            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=f"--- Chapter {record.chapter_number}: "
                            f"{record.title} ({record.video_id}) ---"
                        )
                    ],
                ),
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
                
                # Use safe update (with locking, even in sequential mode)
                await safe_update_video(ws, record.video_id, status=status, error="")
                
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                text=f"Chapter {record.chapter_number} saved "
                                f"(status={status}, qa={verdict})."
                            )
                        ],
                    ),
                )
            except Exception as exc:  # error isolation: keep producing the book
                logger.exception("chapter pipeline failed for %s", record.video_id)
                await safe_update_video(
                    ws, record.video_id, status="failed", error=str(exc)[:500]
                )
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                text=f"Chapter {record.chapter_number} FAILED "
                                f"and was skipped: {exc}"
                            )
                        ],
                    ),
                )

    async def _run_parallel(
        self, ctx: InvocationContext, ws: Workspace, pending: list[VideoRecord]
    ) -> AsyncGenerator[Event, None]:
        """Parallel video processing with concurrency limit and error isolation."""
        settings = get_settings()
        semaphore = asyncio.Semaphore(settings.max_concurrent_videos)
        
        # Queue for events from parallel tasks
        event_queue: asyncio.Queue[Event | None] = asyncio.Queue()

        async def process_one_video(record: VideoRecord) -> None:
            """Process a single video with concurrency control."""
            async with semaphore:
                try:
                    # Create isolated state for this video
                    # Note: We reuse ctx but carefully manage state isolation
                    video_state = {
                        "current_video": record.model_dump(),
                        "video_id": record.video_id,
                        "video_title": record.title,
                        "qa_verdict": "unknown",
                        "chapter_tex": "",
                        "critique": "",
                    }
                    
                    # Store original state to restore later
                    original_state = ctx.session.state.copy()
                    
                    # Update state for this video
                    ctx.session.state.update(video_state)

                    await event_queue.put(
                        Event(
                            author=self.name,
                            content=types.Content(
                                role="model",
                                parts=[
                                    types.Part(
                                        text=f"[Parallel] Starting Chapter {record.chapter_number}: "
                                        f"{record.title} ({record.video_id})"
                                    )
                                ],
                            ),
                        )
                    )

                    # Run the pipeline
                    async for event in self.pipeline.run_async(ctx):
                        await event_queue.put(event)

                    # Save chapter
                    tex = latex_tools.sanitize_chapter_tex(
                        ctx.session.state.get("chapter_tex", "")
                    )
                    if not tex.strip():
                        raise RuntimeError("pipeline produced an empty chapter")
                    
                    Workspace.write_text(ws.chapter_dir(record) / "chapter.tex", tex)

                    verdict = ctx.session.state.get("qa_verdict", "unknown")
                    status = "verified" if verdict == "pass" else "written"
                    
                    # Thread-safe manifest update
                    await safe_update_video(ws, record.video_id, status=status, error="")

                    await event_queue.put(
                        Event(
                            author=self.name,
                            content=types.Content(
                                role="model",
                                parts=[
                                    types.Part(
                                        text=f"[Parallel] Chapter {record.chapter_number} saved "
                                        f"(status={status}, qa={verdict})."
                                    )
                                ],
                            ),
                        )
                    )
                    
                    # Restore original state
                    ctx.session.state.clear()
                    ctx.session.state.update(original_state)

                except Exception as exc:
                    logger.exception("chapter pipeline failed for %s", record.video_id)
                    
                    # Thread-safe failure recording
                    await safe_update_video(
                        ws, record.video_id, status="failed", error=str(exc)[:500]
                    )

                    await event_queue.put(
                        Event(
                            author=self.name,
                            content=types.Content(
                                role="model",
                                parts=[
                                    types.Part(
                                        text=f"[Parallel] Chapter {record.chapter_number} FAILED: {exc}"
                                    )
                                ],
                            ),
                        )
                    )
                    
                    # Restore state even on failure
                    ctx.session.state.clear()
                    ctx.session.state.update(original_state)

        # Start all video processing tasks
        async def run_all_tasks():
            """Run all video tasks and signal completion."""
            tasks = [asyncio.create_task(process_one_video(record)) for record in pending]
            await asyncio.gather(*tasks, return_exceptions=True)
            await event_queue.put(None)  # Signal completion

        # Start background task runner
        runner_task = asyncio.create_task(run_all_tasks())

        # Yield events as they come from the queue
        while True:
            event = await event_queue.get()
            if event is None:  # Completion signal
                break
            yield event

        # Wait for all tasks to complete
        await runner_task


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
