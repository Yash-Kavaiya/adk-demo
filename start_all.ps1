# Start MLflow Tracking Server and Google ADK Web UI concurrently
$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting BookForge (Google ADK + MLflow Observability)  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start MLflow Server on Port 5000 with SQLite backend
Write-Host "[1/2] Launching MLflow Server on http://127.0.0.1:5000 ..." -ForegroundColor Yellow
$mlflowProcess = Start-Process -FilePath "python" -ArgumentList "-m mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000" -PassThru -NoNewWindow

# 2. Start ADK Web UI on Port 8000
Write-Host "[2/2] Launching Google ADK Web UI on http://127.0.0.1:8000 ..." -ForegroundColor Green
$adkProcess = Start-Process -FilePath "adk" -ArgumentList "web" -PassThru -NoNewWindow

Write-Host ""
Write-Host "✨ Services are up and running!" -ForegroundColor Magenta
Write-Host "   📊 MLflow Dashboard: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "   🤖 ADK Web UI:       http://127.0.0.1:8000" -ForegroundColor Green
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
