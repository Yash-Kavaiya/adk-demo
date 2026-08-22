"""Robust JSON extraction and model resolution for Google ADK agents in BookForge."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI
from google.adk.labs.openai import OpenAILlm
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from bookforge.config import Settings

logger = logging.getLogger(__name__)


def extract_clean_json(text: str) -> str:
    """Extract valid JSON from raw LLM output which might contain markdown, duplicate braces, or thinking artifacts."""
    text = text.strip()

    # Strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()

    # Try parsing directly
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "chapter_title" in data:
            return text
    except json.JSONDecodeError:
        pass

    # Find candidate boundaries for balanced JSON objects and find the one that has chapter_title
    starts = [i for i, c in enumerate(text) if c == "{"]
    ends = [i for i, c in enumerate(text) if c == "}"]

    valid_candidates: list[tuple[int, str]] = []
    for start in starts:
        for end in reversed(ends):
            if end > start:
                candidate = text[start : end + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "chapter_title" in parsed:
                        return candidate
                    if isinstance(parsed, dict):
                        valid_candidates.append((len(candidate), candidate))
                except json.JSONDecodeError:
                    continue

    if valid_candidates:
        # Return largest valid candidate JSON
        valid_candidates.sort(key=lambda x: x[0], reverse=True)
        return valid_candidates[0][1]

    return text


class RobustNvidiaLlm(OpenAILlm):
    """OpenAILlm subclass configured for NVIDIA NIM with JSON sanitization and extra options."""

    extra_body: dict[str, Any] | None = None

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        async for resp in super().generate_content_async(llm_request, stream=stream):
            if not resp.partial and resp.content and resp.content.parts:
                for part in resp.content.parts:
                    if part.text and llm_request.config and llm_request.config.response_schema:
                        part.text = extract_clean_json(part.text)
            yield resp


def resolve_model(model_name: str, settings: Settings) -> str | BaseLlm:
    """Resolve a model name string to an LLM provider instance or model identifier.

    If an OpenAI / NVIDIA base_url is configured and the model is not a standard
    Gemini model name, returns a RobustNvidiaLlm instance configured with the custom
    endpoint and API key. Otherwise returns the model string for default ADK handling.
    """
    if settings.openai_api_base and settings.openai_api_key:
        if not model_name.startswith("gemini-"):
            return RobustNvidiaLlm(
                model=model_name,
                max_tokens=16384,
                client=AsyncOpenAI(
                    base_url=settings.openai_api_base,
                    api_key=settings.openai_api_key,
                ),
            )
    return model_name
