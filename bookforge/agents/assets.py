"""VisualAssetAgent: turn the analysis spec into real files on disk.

Deterministic by design: charts are rendered by matplotlib from the analyst's
validated data (never hand-drawn by an LLM), tables become booktabs fragments,
and the best frames are copied into the chapter figures directory.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from bookforge.config import get_settings
from bookforge.schemas import (
    AssetsManifest,
    FigureAsset,
    MediaBundle,
    TableAsset,
    VideoRecord,
    coerce_analysis,
)
from bookforge.tools import frames as frame_tools
from bookforge.tools import latex as latex_tools
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)


def _mm_ss(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


class VisualAssetAgent(BaseAgent):
    name: str = "visual_assets"
    description: str = (
        "Renders charts (matplotlib), booktabs table fragments and curated "
        "screenshots into the chapter directory and publishes an assets "
        "manifest the writer must reference verbatim."
    )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        settings = get_settings()
        state = ctx.session.state
        record = VideoRecord.model_validate(state["current_video"])
        analysis = coerce_analysis(state["analysis_json"])

        ws = Workspace(settings.workspace_root_abs, state["channel_slug"])
        vdir = ws.video_dir(record.video_id)
        chapter_dir = ws.chapter_dir(record)

        def rel(path) -> str:
            return path.relative_to(ws.root).as_posix()

        nn = record.chapter_number

        # 1) Tables -> booktabs fragments
        tables: list[TableAsset] = []
        for i, spec in enumerate(analysis.tables, start=1):
            frag = latex_tools.render_table_fragment(
                spec, chapter_dir / "tables" / f"table_{i}.tex"
            )
            tables.append(
                TableAsset(
                    tex_file=rel(frag),
                    caption=spec.caption,
                    label=f"tab:ch{nn:02d}-{i}",
                )
            )

        # 2) Charts -> vector PDFs
        figures: list[FigureAsset] = []
        for i, spec in enumerate(analysis.charts, start=1):
            pdf = latex_tools.render_chart(
                spec, chapter_dir / "figures" / f"chart_{i}.pdf"
            )
            figures.append(
                FigureAsset(
                    filename=rel(pdf),
                    kind="chart",
                    caption=spec.caption,
                    label=f"fig:ch{nn:02d}-chart{i}",
                )
            )

        # 3) Curated frames -> figures (spread across the video timeline)
        bundle = MediaBundle.model_validate_json(
            (vdir / "media.json").read_text(encoding="utf-8")
        )
        curated = frame_tools.curate_frames(
            bundle.frames,
            vdir,
            chapter_dir / "figures",
            settings.max_frames_per_chapter,
        )
        overrides = analysis.frame_captions_dict
        for j, frame in enumerate(curated, start=1):
            caption = overrides.get(frame.file) or (
                f"Video frame at {_mm_ss(frame.timestamp_sec)} illustrating "
                f"the segment discussed in this chapter."
            )
            figures.append(
                FigureAsset(
                    filename=rel(chapter_dir / "figures" / frame.file),
                    kind="frame",
                    caption=caption,
                    label=f"fig:ch{nn:02d}-frame{j}",
                )
            )

        manifest = AssetsManifest(
            chapter_slug=chapter_dir.name,
            chapter_dir=rel(chapter_dir),
            figures=figures,
            tables=tables,
        )
        Workspace.write_text(
            chapter_dir / "assets.json", manifest.model_dump_json(indent=2)
        )
        ws.update_video(record.video_id, status="assets", error="")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"Assets for chapter {nn}: {len(figures)} figures "
                        f"({len(curated)} frames, {len(analysis.charts)} charts), "
                        f"{len(tables)} tables."
                    )
                ],
            ),
            actions=EventActions(
                state_delta={"assets_manifest": manifest.model_dump(mode="json")}
            ),
        )
