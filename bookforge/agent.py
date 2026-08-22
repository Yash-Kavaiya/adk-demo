"""ADK entrypoint: exposes `root_agent` for `adk run bookforge` / `adk web`.

Usage:
    adk run bookforge        # then paste a YouTube channel URL
    adk web                  # pick "bookforge", paste the URL in chat
"""

from bookforge.agents.orchestrator import build_root_agent
from bookforge.config import get_settings

root_agent = build_root_agent(get_settings())
