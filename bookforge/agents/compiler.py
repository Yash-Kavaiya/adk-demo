"""BookCompilerAgent: assemble main.tex from verified chapters -> book.pdf."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from bookforge.config import get_settings
from bookforge.tools import latex as latex_tools
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)


class BookCompilerAgent(BaseAgent):
    name: str = "book_compiler"
    description: str = (
        "Assembles the book preamble, title page, TOC and every completed "
        "chapter into main.tex, compiles with pdflatex and publishes book.pdf."
    )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        settings = get_settings()
        state = ctx.session.state
        ws = Workspace(settings.workspace_root_abs, state["channel_slug"])
        manifest = ws.load_manifest()

        completed = [
            v
            for v in sorted(manifest.videos, key=lambda x: x.chapter_number)
            if v.status in ("verified", "written")
        ]
        failed = [v for v in manifest.videos if v.status == "failed"]
        if not completed:
            raise RuntimeError("No completed chapters — nothing to compile.")

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"Compiling book from {len(completed)} completed chapters "
                        f"({len(failed)} failed excluded). This can take a few minutes."
                    )
                ],
            ),
        )

        chapter_rel_dirs = []
        for record in completed:
            chapter_dir = ws.chapter_dir(record)
            ch_tex_path = chapter_dir / "chapter.tex"
            if ch_tex_path.exists():
                raw_tex = Workspace.read_text(ch_tex_path)
                clean_tex = latex_tools.sanitize_chapter_tex(raw_tex)
                Workspace.write_text(ch_tex_path, clean_tex)
                chapter_rel_dirs.append(chapter_dir.relative_to(ws.root).as_posix())
            else:
                logger.warning("chapter.tex missing for %s — skipped", record.video_id)

        book_title = (
            f"{manifest.channel_title or 'YouTube Channel'} — The Complete Book"
        )
        author_line = "Compiled by BookForge (Google ADK multi-agent pipeline)"

        Workspace.write_text(ws.root / "preamble.tex", latex_tools.PREAMBLE)
        main_tex = Workspace.write_text(
            ws.root / "main.tex",
            latex_tools.assemble_main_tex(book_title, author_line, chapter_rel_dirs),
        )

        compile_ok, log_tail = False, "compile disabled"
        if settings.compile_latex:
            compile_ok, log_tail = latex_tools.compile_tex(
                main_tex, ws.book_dir, passes=2, cwd=ws.root
            )
            produced = ws.book_dir / "main.pdf"
            if compile_ok and produced.exists():
                produced.replace(ws.book_dir / "book.pdf")

        book_meta = {
            "title": book_title,
            "channel_url": manifest.channel_url,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "chapters_included": len(chapter_rel_dirs),
            "chapters_failed": [v.video_id for v in failed],
            "pdf": "book/book.pdf" if (ws.book_dir / "book.pdf").exists() else None,
        }
        Workspace.write_text(
            ws.book_dir / "book_manifest.json", json.dumps(book_meta, indent=2)
        )

        if settings.compile_latex and not compile_ok:
            logger.error("book compile failed:\n%s", log_tail)
            raise RuntimeError(f"pdflatex failed on the book: {log_tail[:800]}")

        pdf_path = book_meta["pdf"] or "(compile disabled)"
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"Book compiled: {len(chapter_rel_dirs)} chapters "
                        f"({len(failed)} videos failed and were excluded). "
                        f"PDF: {pdf_path}"
                    )
                ],
            ),
            actions=EventActions(
                state_delta={
                    "book_pdf": book_meta["pdf"],
                    "chapters_included": len(chapter_rel_dirs),
                    "chapters_failed": len(failed),
                }
            ),
        )
