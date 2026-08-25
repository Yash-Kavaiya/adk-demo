#!/bin/bash
# Start MLflow Tracking Server and Google ADK Web UI concurrently.
# OTEL env vars MUST be set before `adk web` so ADK attaches both its
# in-memory Session/Trace exporters and the MLflow OTLP exporter.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/.venv/Scripts/python.exe"
  ADK="$ROOT/.venv/Scripts/adk.exe"
elif [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
  ADK="$ROOT/.venv/bin/adk"
else
  PY="${PYTHON:-python}"
  ADK="${ADK:-adk}"
fi

export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-http://127.0.0.1:5000}"
export MLFLOW_EXPERIMENT_NAME="${MLFLOW_EXPERIMENT_NAME:-my-experiment}"

echo "=========================================================="
echo "  Starting BookForge (Google ADK + MLflow Observability)  "
echo "=========================================================="

echo "[1/2] Launching MLflow Server on $MLFLOW_TRACKING_URI ..."
"$PY" -m mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000 &
MLFLOW_PID=$!

echo "Waiting for MLflow..."
for _ in $(seq 1 40); do
  if "$PY" -c "import urllib.request,os; urllib.request.urlopen(os.environ['MLFLOW_TRACKING_URI']+'/health', timeout=1)" 2>/dev/null; then
    break
  fi
  sleep 1
done

eval "$("$PY" - <<'PY'
import os
import mlflow

uri = os.environ["MLFLOW_TRACKING_URI"].rstrip("/")
name = os.environ["MLFLOW_EXPERIMENT_NAME"]
mlflow.set_tracking_uri(uri)
exp = mlflow.set_experiment(name)
exp_id = exp.experiment_id
print(f'export OTEL_EXPORTER_OTLP_ENDPOINT={uri}')
print(f'export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT={uri}/v1/traces')
print("export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf")
print("export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf")
print(f'export OTEL_EXPORTER_OTLP_HEADERS=x-mlflow-experiment-id={exp_id}')
print("export OTEL_SERVICE_NAME=bookforge-adk-agent")
print(f'echo "[otel] experiment {name} id={exp_id}"')
PY
)"

echo "[2/2] Launching Google ADK Web UI on http://127.0.0.1:8000 ..."
"$ADK" web --host 127.0.0.1 --port 8000 --no-reload bookforge &
ADK_PID=$!

echo ""
echo "Services are up:"
echo "   MLflow Dashboard: http://127.0.0.1:5000  (experiment: $MLFLOW_EXPERIMENT_NAME)"
echo "   ADK Web UI:       http://127.0.0.1:8000  (app: bookforge)"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $MLFLOW_PID $ADK_PID 2>/dev/null; exit" INT TERM
wait
