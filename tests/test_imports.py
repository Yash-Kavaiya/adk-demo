"""Smoke test: the entire import chain loads without error.

This catches circular imports, missing dependencies, and module-level
crashes before any test that hits an LLM or the network.
"""

import importlib

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "bookforge",
        "bookforge.config",
        "bookforge.schemas",
        "bookforge.prompts",
        "bookforge.tools",
        "bookforge.tools.workspace",
        "bookforge.tools.latex",
        "bookforge.tools.frames",
        "bookforge.tools.youtube",
        "bookforge.agents",
        "bookforge.agents.intake",
        "bookforge.agents.media",
        "bookforge.agents.analyst",
        "bookforge.agents.assets",
        "bookforge.agents.writer",
        "bookforge.agents.critic",
        "bookforge.agents.compiler",
        "bookforge.agents.orchestrator",
        "bookforge.agent",
        "bookforge.main",
    ],
)
def test_module_imports(module):
    importlib.import_module(module)


def test_root_agent_constructs():
    """The ADK root_agent object builds without error."""
    from bookforge.agent import root_agent

    assert root_agent is not None
    assert root_agent.name == "bookforge"
    assert len(root_agent.sub_agents) == 3
