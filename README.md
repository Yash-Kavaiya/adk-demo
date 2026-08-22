# 📚 BookForge: YouTube-to-Textbook Multi-Agent System

> **Transform educational YouTube channels into publication-grade textbooks using Google Agent Development Kit (ADK), NVIDIA NIM / OpenAI Models, and MLflow Tracing & Observability.**

[![Google ADK](https://img.shields.io/badge/Google-ADK_2.0-blue.svg)](https://adk.dev)
[![MLflow Observability](https://img.shields.io/badge/MLflow-Tracing_&_Gateway-0194E2.svg)](https://mlflow.org)
[![LaTeX Support](https://img.shields.io/badge/LaTeX-pdflatex-green.svg)](https://miktex.org)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](https://python.org)

---

## 🌟 Key Features

- **Multi-Agent Orchestration**: Built strictly on **Google Agent Development Kit (ADK)**:
  - `ChannelIntakeAgent`: Resolves YouTube channels/playlists into resumable JSON manifests.
  - `MediaAcquisitionAgent`: Downloads audio/video, transcribes via **Faster-Whisper** with timestamps, extracts and deduplicates video slides using **perceptual hashing (pHash)**.
  - `TranscriptAnalystAgent`: Analyzes lectures and extracts structured concepts, tables, charts, and TikZ diagram specs via **NVIDIA NIM (`nvidia/nemotron-3-ultra-550b-a55b`)** or Gemini.
  - `VisualAssetAgent`: Generates vector PDFs for matplotlib charts, TikZ architecture diagrams, and table fragments.
  - `ChapterWriterAgent` & `ChapterCriticAgent`: Authors and verifies LaTeX chapters in an iterative refinement QA loop.
  - `BookCompilerAgent`: Typesets standalone chapters and compiles the master `book.pdf`.
- **Full MLflow Integration (Python & Go)**:
  - **OpenTelemetry Tracing**: Streams OTLP spans directly to MLflow.
  - **AI Gateway Connector**: Routes LLM requests through MLflow's model proxy.
  - **LLM Scorers & Evaluators**: Automated evaluation of generated chapters.
- **Interactive Web UI & CLI**: Run seamlessly from the command line or via the interactive Google ADK Web UI.

---

## 🏗️ Multi-Agent Architecture

```
User Input (YouTube URL)
   │
   ▼
[ChannelIntakeAgent] ──► Generates video manifest (videos.json)
   │
   ▼
[SequentialAgent: Chapter Production Pipeline] (Per Video)
   ├── [MediaAcquisitionAgent] (Video + Whisper Audio + pHash Keyframes)
   ├── [TranscriptAnalystAgent] (Structured JSON Analysis via NVIDIA NIM / Gemini)
   ├── [VisualAssetAgent] (Matplotlib Charts + Booktabs Tables + Keyframe Assets)
   └── [LoopAgent: ChapterRefinementLoop]
         ├── [ChapterWriterAgent] (Academic LaTeX Composition)
         └── [ChapterCriticAgent] (pdflatex Validation + QA Quality Gate)
   │
   ▼
[BookCompilerAgent] ──► Compiles master book.pdf with Table of Contents & Preamble
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- `ffmpeg` installed and on your PATH
- `pdflatex` (MiKTeX or TeXLive) for compiling PDFs

### 2. Installation
```bash
git clone https://github.com/<your-username>/adk-demo.git
cd adk-demo
pip install -e .
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
# Optional: NVIDIA NIM API (or standard OpenAI / Gemini keys)
BOOKFORGE_OPENAI_API_BASE=https://integrate.api.nvidia.com/v1
BOOKFORGE_OPENAI_API_KEY=your_nvidia_or_openai_api_key
BOOKFORGE_MODEL_ANALYST=nvidia/nemotron-3-ultra-550b-a55b
BOOKFORGE_MODEL_WRITER=nvidia/nemotron-3-ultra-550b-a55b
BOOKFORGE_MODEL_CRITIC=nvidia/nemotron-3-ultra-550b-a55b
```

---

## ⚡ Quick Start: One-Command Runner

Run both the **MLflow Tracking Server** and **Google ADK Web UI** simultaneously:

### On Windows (PowerShell):
```powershell
.\start_all.ps1
```

### On Linux / macOS (Bash):
```bash
chmod +x start_all.sh
./start_all.sh
```

- 🤖 **Google ADK Web UI**: `http://127.0.0.1:8000`
- 📊 **MLflow Tracing Dashboard**: `http://127.0.0.1:5000`

---

## 📖 CLI Usage

To run the pipeline directly from the command line:

```bash
# Generate a book from a YouTube channel
python -m bookforge.main "https://www.youtube.com/@vishakha.sadhwani" --max-videos 2 --verbose
```

The compiled PDF will be saved to:
`data/<channel-slug>/book/book.pdf`

---

## 🧪 Testing

Run the full pytest test suite (49 automated unit tests):

```bash
pytest tests/ -v
```

---

## 📄 License
Apache License 2.0.
