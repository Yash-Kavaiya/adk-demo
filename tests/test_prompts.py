"""Instruction templates must not contain accidental ADK state placeholders.

ADK injects session state via {identifier}. A literal TikZ/LaTeX example
like `{label}` raises KeyError: Context variable not found: `label`.
"""

from __future__ import annotations

import re

from bookforge.prompts import (
    ANALYST_INSTRUCTION,
    CRITIC_INSTRUCTION,
    REFINER_INSTRUCTION,
    WRITER_INSTRUCTION,
)

# Same pattern ADK uses in google.adk.utils.instructions_utils
_TEMPLATE_VAR_PATTERN = re.compile(r"{+[^{}]*}+")

ALLOWED_PLACEHOLDERS = {
    "video_title",
    "transcript",
    "analysis_json",
    "assets_manifest",
    "chapter_tex",
    "critique",
}

INSTRUCTIONS = {
    "analyst": ANALYST_INSTRUCTION,
    "writer": WRITER_INSTRUCTION,
    "critic": CRITIC_INSTRUCTION,
    "refiner": REFINER_INSTRUCTION,
}


def required_placeholders(template: str) -> set[str]:
    found: set[str] = set()
    for match in _TEMPLATE_VAR_PATTERN.finditer(template):
        name = match.group().lstrip("{").rstrip("}").strip()
        if name.endswith("?"):
            continue
        if name.isidentifier():
            found.add(name)
    return found


def test_writer_has_no_literal_label_placeholder():
    found = required_placeholders(WRITER_INSTRUCTION)
    assert "label" not in found, (
        "WRITER_INSTRUCTION contains `{label}`, which ADK treats as a "
        "session-state injection and crashes chapter writing with "
        "'Context variable not found: label.'"
    )


def test_all_instruction_placeholders_are_allowlisted():
    unexpected: dict[str, set[str]] = {}
    for name, text in INSTRUCTIONS.items():
        extra = required_placeholders(text) - ALLOWED_PLACEHOLDERS
        if extra:
            unexpected[name] = extra
    assert unexpected == {}, f"Accidental ADK placeholders: {unexpected}"
