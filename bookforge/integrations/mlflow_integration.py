"""MLflow observability for Google ADK (official OTLP tracing spec).

Official spec:
https://mlflow.org/docs/latest/genai/tracing/integrations/listing/google-adk/

  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:5000
  export OTEL_EXPORTER_OTLP_HEADERS=x-mlflow-experiment-id=<id>

plus an OTLP HTTP span exporter. ADK Web already installs a TracerProvider so
its Sessions and Trace tabs work. Replacing that provider is what made both
tabs go empty. We only *add* an OTLP exporter to an existing SDK provider.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from urllib.request import urlopen

logger = logging.getLogger(__name__)

DEFAULT_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_EXPERIMENT_NAME = "my-experiment"
SERVICE_NAME = "bookforge-adk-agent"
# Must match the ADK Web UI default so CLI sessions show up in the session list.
ADK_WEB_USER_ID = "user"

_STATE: dict[str, Any] = {
    "enabled": False,
    "experiment_id": None,
    "tracking_uri": None,
    "provider": None,
}


def session_db_path() -> Path:
    """Shared SQLite file used by `adk web` and `python -m bookforge.main`."""
    return Path(__file__).resolve().parents[1] / ".adk" / "session.db"


def create_session_service():
    """Persist sessions where the Python ADK Web UI can list them."""
    from google.adk.sessions.sqlite_session_service import SqliteSessionService

    path = session_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSessionService(db_path=str(path))


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _tracking_reachable(uri: str, timeout: float = 2.0) -> bool:
    base = uri.rstrip("/")
    for suffix in ("/health", ""):
        try:
            urlopen(base + suffix, timeout=timeout)
            return True
        except Exception:
            continue
    return False


def apply_otel_env(uri: str, exp_id: str) -> None:
    """Set the official MLflow Google ADK OpenTelemetry environment variables."""
    base = uri.rstrip("/")
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = base
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{base}/v1/traces"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"
    os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"x-mlflow-experiment-id={exp_id}"
    os.environ.setdefault("OTEL_SERVICE_NAME", SERVICE_NAME)


def _sdk_provider():
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    provider = trace.get_tracer_provider()
    return provider if isinstance(provider, TracerProvider) else None


def _has_otlp_processor(provider) -> bool:
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        return False
    processors = getattr(provider, "_active_span_processor", None)
    children = getattr(processors, "_span_processors", ()) or ()
    for proc in children:
        exporter = getattr(proc, "span_exporter", None)
        if isinstance(exporter, OTLPSpanExporter):
            return True
    return False


def _attach_otlp_exporter(provider, uri: str, exp_id: str) -> None:
    if _has_otlp_processor(provider):
        return
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    # Official MLflow ADK snippet uses SimpleSpanProcessor so short CLI runs
    # are not dropped by BatchSpanProcessor's queue.
    exporter = OTLPSpanExporter(
        endpoint=f"{uri.rstrip('/')}/v1/traces",
        headers={"x-mlflow-experiment-id": str(exp_id)},
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))


def setup_mlflow_tracing(
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
) -> bool:
    """Stream ADK OpenTelemetry spans to MLflow without breaking ADK Web traces."""
    if _env_flag("BOOKFORGE_DISABLE_MLFLOW_TRACING"):
        return False
    try:
        import mlflow
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
        exp_name = experiment_name or os.getenv(
            "MLFLOW_EXPERIMENT_NAME", DEFAULT_EXPERIMENT_NAME
        )

        if not _tracking_reachable(uri):
            logger.warning(
                "MLflow tracking server not reachable at %s; traces disabled", uri
            )
            return False

        mlflow.set_tracking_uri(uri)
        experiment = mlflow.set_experiment(exp_name)
        exp_id = str(getattr(experiment, "experiment_id", "0"))
        apply_otel_env(uri, exp_id)

        try:
            google_adk = getattr(mlflow, "google_adk", None)
            if google_adk is not None and hasattr(google_adk, "autolog"):
                google_adk.autolog()
            elif hasattr(mlflow, "gemini") and hasattr(mlflow.gemini, "autolog"):
                mlflow.gemini.autolog()
        except Exception as exc:
            logger.debug("MLflow autolog notice: %s", exc)

        existing = _sdk_provider()
        if existing is not None:
            # ADK Web already owns this provider (Sessions/Trace tabs).
            _attach_otlp_exporter(existing, uri, exp_id)
            provider = existing
        else:
            provider = TracerProvider(
                resource=Resource.create(
                    {
                        "service.name": SERVICE_NAME,
                        "mlflow.experiment.id": exp_id,
                    }
                )
            )
            _attach_otlp_exporter(provider, uri, exp_id)
            trace.set_tracer_provider(provider)

        _STATE.update(
            enabled=True,
            experiment_id=exp_id,
            tracking_uri=uri,
            provider=provider,
        )
        logger.info(
            "MLflow tracing initialized on experiment '%s' (ID %s) at %s",
            exp_name,
            exp_id,
            uri,
        )
        return True
    except Exception as exc:
        logger.warning("Could not initialize MLflow tracing: %s", exc)
        return False


def flush_mlflow_tracing(timeout_millis: int = 5000) -> None:
    """Force pending spans to MLflow (needed after CLI / smoke runs)."""
    provider = _STATE.get("provider") or _sdk_provider()
    if provider is None or not hasattr(provider, "force_flush"):
        return
    try:
        provider.force_flush(timeout_millis=timeout_millis)
    except Exception as exc:
        logger.debug("MLflow trace flush failed: %s", exc)


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
        return mlflow.evaluate(
            data=df,
            targets="target",
            predictions="prediction",
            model_type="text",
            extra_metrics=scorers or [],
        )
    except Exception as exc:
        logger.warning("MLflow evaluation failed: %s", exc)
        return None
