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
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
) -> bool:
    """Configure Google ADK OpenTelemetry spans to stream directly to MLflow.

    Target experiment: my-experiment (or MLFLOW_EXPERIMENT_NAME env variable).
    """
    try:
        import mlflow

        uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
        exp_name = experiment_name or os.getenv("MLFLOW_EXPERIMENT_NAME", "my-experiment")

        mlflow.set_tracking_uri(uri)
        experiment = mlflow.set_experiment(exp_name)
        exp_id = getattr(experiment, "experiment_id", "1")

        # Set official MLflow Google ADK OpenTelemetry environment variables
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = uri
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"x-mlflow-experiment-id={exp_id}"

        # Enable framework-level autologging
        try:
            if hasattr(mlflow, "gemini") and hasattr(mlflow.gemini, "autolog"):
                mlflow.gemini.autolog()
            elif hasattr(mlflow, "autolog"):
                mlflow.autolog(log_traces=True)
        except Exception as e:
            logger.debug("Auto-logging notice: %s", e)

        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        otlp_endpoint = f"{uri.rstrip('/')}/v1/traces"
        resource = Resource.create({
            "service.name": "bookforge-adk-agent",
            "mlflow.experiment.id": exp_id,
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers={"x-mlflow-experiment-id": str(exp_id)},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        logger.info("MLflow tracing initialized on experiment '%s' (ID %s) at %s", exp_name, exp_id, uri)
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
