"""Chapter QA loop: critic (verify-by-execution) + refiner, bounded.

The critic doesn't just *read* the chapter — it writes it to disk and runs a
real pdflatex pass, then checks every referenced asset exists. Approve ->
escalate (exits the LoopAgent). Otherwise the critique feeds the refiner.
"""

from __future__ import annotations

import logging

from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import FunctionTool, ToolContext

from bookforge.agents.model_resolver import resolve_model
from bookforge.agents.writer import make_refiner_agent
from bookforge.config import Settings, get_settings
from bookforge.prompts import CRITIC_INSTRUCTION
from bookforge.schemas import VideoRecord
from bookforge.tools import latex as latex_tools
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Critic tools (ToolContext gives real access to session state)
# ---------------------------------------------------------------------------


def compile_chapter(tool_context: ToolContext) -> dict:
    """Write the current chapter body to disk and compile it with pdflatex.

    Returns ok, plus missing referenced files and compiler errors when the
    build fails. The chapter is compiled standalone with the shared book
    preamble, cwd = workspace root, so root-relative asset paths resolve
    exactly as they will in the final book.
    """
    settings = get_settings()
    state = tool_context.state
    record = VideoRecord.model_validate(state["current_video"])
    ws = Workspace(settings.workspace_root_abs, state["channel_slug"])

    tex = latex_tools.sanitize_chapter_tex(state.get("chapter_tex", ""))
    if not tex.strip():
        return {"ok": False, "errors": "chapter_tex is empty"}

    chapter_dir = ws.chapter_dir(record)
    Workspace.write_text(chapter_dir / "chapter.tex", tex)

    missing = [
        ref
        for ref in latex_tools.find_referenced_files(tex)
        if not (ws.root / ref).exists()
    ]

    result: dict = {"ok": True, "missing_files": missing}
    if missing:
        result["ok"] = False
        result["errors"] = "Referenced files missing: " + ", ".join(missing)
        return result

    if not settings.compile_latex:
        result["skipped_compile"] = True
        return result

    qa_dir = ws.build_dir / f"qa_{record.video_id}"
    wrapper = latex_tools.chapter_wrapper(latex_tools.PREAMBLE, tex)
    Workspace.write_text(qa_dir / "main_qa.tex", wrapper)
    ok, log = latex_tools.compile_tex(
        qa_dir / "main_qa.tex", qa_dir, passes=1, cwd=ws.root
    )
    result["ok"] = ok
    if not ok:
        result["errors"] = log
    return result


def approve_chapter(tool_context: ToolContext) -> dict:
    """Approve the chapter: mark QA passed and exit the refinement loop."""
    tool_context.actions.escalate = True
    tool_context.actions.state_delta["qa_verdict"] = "pass"
    return {"approved": True}


# ---------------------------------------------------------------------------
# Agents + loop factory
# ---------------------------------------------------------------------------


def make_critic_agent(settings: Settings) -> LlmAgent:
    return LlmAgent(
        name="chapter_critic",
        model=resolve_model(settings.critic_model, settings),
        description=(
            "Verifies the chapter by actually compiling it and checking asset "
            "references; approves (loop exit) or emits a numbered defect list."
        ),
        instruction=CRITIC_INSTRUCTION,
        tools=[FunctionTool(compile_chapter), FunctionTool(approve_chapter)],
        output_key="critique",
        disallow_transfer_to_parent=True,
    )


def make_qa_loop(settings: Settings) -> LoopAgent:
    return LoopAgent(
        name="chapter_qa_loop",
        description="Bounded verify-and-refine loop (critic + refiner).",
        sub_agents=[make_critic_agent(settings), make_refiner_agent(settings)],
        max_iterations=settings.qa_max_iterations,
    )
