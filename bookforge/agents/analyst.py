from google.adk.agents import LlmAgent

from bookforge.agents.model_resolver import resolve_model
from bookforge.config import Settings
from bookforge.prompts import ANALYST_INSTRUCTION
from bookforge.schemas import ChapterAnalysis


def make_analyst_agent(settings: Settings) -> LlmAgent:
    return LlmAgent(
        name="transcript_analyst",
        model=resolve_model(settings.analyst_model, settings),
        description=(
            "Reads the timestamped transcript and emits a structured chapter "
            "analysis: objectives, concepts, table/chart/diagram specs, "
            "glossary and exercises."
        ),
        instruction=ANALYST_INSTRUCTION,
        output_schema=ChapterAnalysis,
        output_key="analysis_json",
        disallow_transfer_to_parent=True,
    )
