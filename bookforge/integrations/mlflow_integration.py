"""MLflow integration module for Google Agent Development Kit (ADK) in Python.

Provides:
1. MLflow OpenTelemetry Tracing setup (OTLP HTTP Span Exporter).
2. MLflow AI Gateway configuration & client connector.
3. MLflow LLM Evaluator / Scorers integration for ADK agents.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def setup_mlflow_tracing(
    tracking_uri: str = "http://localhost:5000",
    experiment_name: str = "bookforge-adk",
) -> bool:
    """Configure Google ADK OpenTelemetry spans to stream directly to MLflow.

    Requires:
        pip install "mlflow>=3.6.0" opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
    """
    try:
        import mlflow
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Configure MLflow tracking
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

        # Build OTLP endpoint for MLflow Tracing (e.g. http://localhost:5000/v1/traces)
        otlp_endpoint = f"{tracking_uri.rstrip('/')}/v1/traces"

        resource = Resource.create({"service.name": "bookforge-adk-agent"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        logger.info("MLflow OpenTelemetry tracing initialized: %s", otlp_endpoint)
        return True
    except Exception as exc:
        logger.warning("Could not initialize MLflow tracing: %s", exc)
        return False


def get_mlflow_gateway_config(
    gateway_url: str = "http://localhost:5000/v1",
    route_name: str = "chat",
) -> dict[str, str]:
    """Return OpenAI/LiteLLM configuration compatible with MLflow AI Gateway / Proxy."""
    return {
        "openai_api_base": f"{gateway_url.rstrip('/')}/endpoints/{route_name}/invocations",
        "openai_api_key": os.getenv("MLFLOW_API_KEY", "default-key"),
    }


def evaluate_adk_run_with_mlflow(
    predictions: list[str],
    targets: list[str],
    scorers: list[str] | None = None,
) -> Any:
    """Run MLflow GenAI evaluation scorers on ADK generated outputs."""
    try:
        import mlflow
        import pandas as pd

        df = pd.DataFrame({"prediction": predictions, "target": targets})
        eval_results = mlflow.evaluate(
            data=df,
            targets="target",
            predictions="prediction",
            model_type="text",
            extra_metrics=scorers or [],
        )
        return eval_results
    except Exception as exc:
        logger.warning("MLflow evaluation failed: %s", exc)
        return None
