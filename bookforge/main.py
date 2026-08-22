"""BookForge CLI runner.

    python -m bookforge.main "https://www.youtube.com/@SomeChannel"
    python -m bookforge.main <url> --max-videos 2 --session my-run

Streams agent progress to stdout and exits non-zero when the book fails.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from bookforge.agents.orchestrator import build_root_agent
from bookforge.config import Settings, get_settings

logger = logging.getLogger("bookforge")


def preflight_check(settings: Settings) -> list[str]:
    """Validate environment before running the pipeline. Returns warnings."""
    import shutil

    warnings = []

    # Credentials
    has_key = bool(os.environ.get("GOOGLE_API_KEY"))
    has_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE"
    has_openai = bool(settings.openai_api_key or os.environ.get("OPENAI_API_KEY"))
    if not has_key and not has_vertex and not has_openai:
        raise RuntimeError(
            "No LLM credentials found. Set GOOGLE_API_KEY or OPENAI_API_KEY / BOOKFORGE_OPENAI_API_KEY."
        )

    # ffmpeg
    if not shutil.which("ffmpeg"):
        warnings.append(
            "ffmpeg not found on PATH — frame extraction will fail. "
            "Install ffmpeg: https://ffmpeg.org/download.html"
        )

    # pdflatex
    if settings.compile_latex and not shutil.which("pdflatex"):
        warnings.append(
            "pdflatex not found on PATH but COMPILE_LATEX=true — "
            "PDF compilation will be skipped. Install TeX Live or MiKTeX, "
            "or set BOOKFORGE_COMPILE_LATEX=false."
        )
        settings.compile_latex = False

    # Workspace
    logger.info("workspace: %s", settings.workspace_root_abs)

    return warnings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bookforge",
        description="Turn a YouTube channel into a compiled LaTeX book.",
    )
    parser.add_argument("channel_url", help="YouTube channel URL")
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="cap the number of videos (testing)",
    )
    parser.add_argument("--session", default=None, help="session id (default: random)")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> int:
    # Load .env into os.environ so GOOGLE_API_KEY is visible to
    # both the preflight check and the google-genai SDK.
    from dotenv import load_dotenv

    load_dotenv()

    settings = get_settings()
    if args.max_videos is not None:
        settings.max_videos = args.max_videos  # CLI override wins

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else settings.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    warnings = preflight_check(settings)
    for w in warnings:
        logger.warning(w)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=build_root_agent(settings),
        app_name="bookforge",
        session_service=session_service,
    )

    session_id = args.session or f"run-{uuid.uuid4().hex[:8]}"
    session = await session_service.create_session(
        app_name="bookforge", user_id="local", session_id=session_id
    )
    logger.info("session %s | workspace: %s", session_id, settings.workspace_root_abs)

    user_msg = types.Content(
        role="user",
        parts=[
            types.Part(
                text=f"Create a complete book from this YouTube channel: {args.channel_url}"
            )
        ],
    )

    exit_code = 0
    try:
        async for event in runner.run_async(
            user_id="local", session_id=session.id, new_message=user_msg
        ):
            if event.content and event.content.parts:
                text = "".join(p.text or "" for p in event.content.parts).strip()
                if text:
                    print(f"[{event.author}] {text[:500]}", flush=True)
    except Exception as exc:
        logger.exception("pipeline aborted")
        print(f"ERROR: {exc}", file=sys.stderr)
        exit_code = 1

    final = await session_service.get_session(
        app_name="bookforge", user_id="local", session_id=session_id
    )
    final_state = dict(final.state or {}) if final else {}
    book_pdf = final_state.get("book_pdf")
    slug = final_state.get("channel_slug", "")
    if book_pdf:
        print(f"\nBOOK READY: {settings.workspace_root_abs / slug / book_pdf}")
    elif exit_code == 0:
        print(
            "\nRun finished without a book PDF "
            "(compile disabled or all chapters failed).",
            file=sys.stderr,
        )
        exit_code = 2
    return exit_code


def cli_entry() -> None:
    main()


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
