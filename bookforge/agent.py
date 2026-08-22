"""ADK entrypoint: exposes `root_agent` for `adk run bookforge` / `adk web`.

Usage:
    adk run bookforge        # then paste a YouTube channel URL
    adk web                  # pick "bookforge", paste the URL in chat
"""

import os
from bookforge.agents.orchestrator import build_root_agent
from bookforge.config import get_settings
from bookforge.integrations.mlflow_integration import setup_mlflow_tracing

# Automatically stream ADK Web UI traces to MLflow
setup_mlflow_tracing(
    tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"),
    experiment_name=os.getenv("MLFLOW_EXPERIMENT_NAME", "my-experiment"),
)

root_agent = build_root_agent(get_settings())
