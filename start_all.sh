#!/bin/bash
# Start MLflow Tracking Server and Google ADK Web UI concurrently

echo "=========================================================="
echo "  Starting BookForge (Google ADK + MLflow Observability)  "
echo "=========================================================="

# 1. Start MLflow Server
echo "[1/2] Launching MLflow Server on http://127.0.0.1:5000 ..."
python -m mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000 &
MLFLOW_PID=$!

# 2. Start ADK Web UI
echo "[2/2] Launching Google ADK Web UI on http://127.0.0.1:8000 ..."
adk web &
ADK_PID=$!

echo ""
echo "✨ Services are up and running!"
echo "   📊 MLflow Dashboard: http://127.0.0.1:5000"
echo "   🤖 ADK Web UI:       http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $MLFLOW_PID $ADK_PID; exit" SIGINT SIGTERM

wait
