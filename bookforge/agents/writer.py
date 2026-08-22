from google.adk.agents import LlmAgent

from bookforge.agents.model_resolver import resolve_model
from bookforge.config import Settings
from bookforge.prompts import REFINER_INSTRUCTION, WRITER_INSTRUCTION


def make_writer_agent(settings: Settings) -> LlmAgent:
    return LlmAgent(
        name="chapter_writer",
        model=resolve_model(settings.writer_model, settings),
        description=(
            "Composes the full LaTeX chapter body from the validated analysis "
            "and the on-disk assets manifest."
        ),
        instruction=WRITER_INSTRUCTION,
        output_key="chapter_tex",
        disallow_transfer_to_parent=True,
    )


def make_refiner_agent(settings: Settings) -> LlmAgent:
    return LlmAgent(
        name="chapter_refiner",
        model=resolve_model(settings.writer_model, settings),
        description=(
            "Rewrites the chapter to fix every defect found by the critic "
            "while preserving what already works."
        ),
        instruction=REFINER_INSTRUCTION,
        output_key="chapter_tex",
        disallow_transfer_to_parent=True,
    )
