"""BookProductionAgent (resumable per-video loop) + root graph builder."""

from __future__ import annotations

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
from bookforge.tools import latex as latex_tools
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)


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

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Producing {len(pending)} chapters.")],
            ),
        )

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
                ws.update_video(record.video_id, status=status, error="")
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
                ws.update_video(record.video_id, status="failed", error=str(exc)[:500])
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

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"production_done": True}),
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
