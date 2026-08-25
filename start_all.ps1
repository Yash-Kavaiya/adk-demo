# Start MLflow Tracking Server and Google ADK Web UI concurrently.
# OTEL env vars MUST be set before `adk web` so ADK attaches both its
# in-memory Session/Trace exporters and the MLflow OTLP exporter.
$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Adk = Join-Path $Root ".venv\Scripts\adk.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
if (-not (Test-Path $Adk)) { $Adk = "adk" }

if (-not $env:MLFLOW_TRACKING_URI) { $env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000" }
if (-not $env:MLFLOW_EXPERIMENT_NAME) { $env:MLFLOW_EXPERIMENT_NAME = "my-experiment" }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting BookForge (Google ADK + MLflow Observability)  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "[1/2] Launching MLflow Server on $($env:MLFLOW_TRACKING_URI) ..." -ForegroundColor Yellow
$mlflowProcess = Start-Process -FilePath $Py -ArgumentList "-m mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000" -PassThru -NoNewWindow

Write-Host "Waiting for MLflow..."
for ($i = 0; $i -lt 40; $i++) {
    try {
        Invoke-WebRequest -Uri "$($env:MLFLOW_TRACKING_URI)/health" -TimeoutSec 1 -UseBasicParsing | Out-Null
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

$otel = & $Py -c @"
import os, mlflow
uri = os.environ['MLFLOW_TRACKING_URI'].rstrip('/')
name = os.environ['MLFLOW_EXPERIMENT_NAME']
mlflow.set_tracking_uri(uri)
exp = mlflow.set_experiment(name)
print(exp.experiment_id)
"@
$env:OTEL_EXPORTER_OTLP_ENDPOINT = $env:MLFLOW_TRACKING_URI.TrimEnd("/")
$env:OTEL_EXPORTER_OTLP_TRACES_ENDPOINT = "$($env:OTEL_EXPORTER_OTLP_ENDPOINT)/v1/traces"
$env:OTEL_EXPORTER_OTLP_TRACES_PROTOCOL = "http/protobuf"
$env:OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"
$env:OTEL_EXPORTER_OTLP_HEADERS = "x-mlflow-experiment-id=$otel"
$env:OTEL_SERVICE_NAME = "bookforge-adk-agent"
Write-Host "[otel] experiment $($env:MLFLOW_EXPERIMENT_NAME) id=$otel" -ForegroundColor Cyan

Write-Host "[2/2] Launching Google ADK Web UI on http://127.0.0.1:8000 ..." -ForegroundColor Green
$adkProcess = Start-Process -FilePath $Adk -ArgumentList "web --host 127.0.0.1 --port 8000 --no-reload bookforge" -PassThru -NoNewWindow

Write-Host ""
Write-Host "Services are up:" -ForegroundColor Magenta
Write-Host "   MLflow Dashboard: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "   ADK Web UI:       http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to terminate both servers..." -ForegroundColor Gray

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "Stopping servers..." -ForegroundColor Red
    Stop-Process -Id $mlflowProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $adkProcess.Id -Force -ErrorAction SilentlyContinue
}
