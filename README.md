# BookForge — YouTube Channel → Book (Google ADK multi-agent system)

Give BookForge a **YouTube channel URL**; it produces a **compiled, print-ready
PDF book** (`book/book.pdf`) plus the full LaTeX source tree — one chapter per
video with study notes, tables, charts, TikZ diagrams, curated screenshots,
glossary and exercises.

Built on the [Google Agent Development Kit (ADK)](https://adk.dev/).
See [`PLAN.md`](PLAN.md) for the enhanced flow and
[`solution-architecture.md`](solution-architecture.md) for the system design.

## The agent graph

```
bookforge (SequentialAgent)
├── ChannelIntakeAgent        channel URL -> manifest/videos.json (resumable)
├── BookProductionAgent       loop over pending videos, checkpointed
│   └── chapter_pipeline (SequentialAgent, once per video)
│       ├── MediaAcquisitionAgent   download · captions→whisper · frames + pHash dedupe
│       ├── TranscriptAnalystAgent  Gemini Flash -> ChapterAnalysis JSON (structured)
│       ├── VisualAssetAgent        matplotlib charts · booktabs tables · figures
│       ├── ChapterWriterAgent      Gemini Pro -> chapter.tex
│       └── chapter_qa_loop (LoopAgent, max 3)
│           ├── ChapterCriticAgent  real pdflatex compile + asset checks -> approve/critique
│           └── ChapterRefinerAgent rewrite from the critique
└── BookCompilerAgent         main.tex + pdflatex -> book.pdf
```

Deterministic stages (download, frames, charts, compiling) are **code** — LLM
tokens are spent only on analysis, writing and critique.

## Quickstart

```bash
python -m venv .venv && .venv\Scripts\activate    # or source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                               # then set GOOGLE_API_KEY
```

System prerequisites: **ffmpeg** and a LaTeX toolchain (**pdflatex**, e.g.
MiKTeX/TeX Live) on PATH — both optional but required for frames and PDF
output (set `BOOKFORGE_COMPILE_LATEX=false` to skip PDF builds).

Run a channel:

```bash
python -m bookforge.main "https://www.youtube.com/@YourChannel"
python -m bookforge.main "https://www.youtube.com/@YourChannel" --max-videos 2   # smoke run
```

Or via the ADK toolchain:

```bash
adk run bookforge     # paste the channel URL when prompted
adk web               # interactive UI with event/trace inspection
```

Output lands in `data/<channel-slug>/`:

```
manifest.json            # per-video status: pending|media|analyzed|assets|written|verified|failed
videos/<id>/             # video.mp4, transcript.txt, media.json, frames_raw/
chapters/<NN>_<title>/   # chapter.tex, figures/, tables/, assets.json
book/book.pdf            # the final book (+ book_manifest.json)
```

**Resume:** just run the same command again — verified chapters are skipped,
failed ones retried.

## Configuration

All settings are env vars with the `BOOKFORGE_` prefix (see
[`.env.example`](.env.example) for the full list). Highlights:

| Setting | Default | Purpose |
|---|---|---|
| `ANALYST_MODEL` / `WRITER_MODEL` / `CRITIC_MODEL` | flash / pro / flash | per-stage model routing |
| `FRAME_INTERVAL_SEC` | `5` | screenshot cadence |
| `FRAME_PHASH_THRESHOLD` | `6` | dedupe strictness (hamming) |
| `MAX_FRAMES_PER_CHAPTER` | `12` | curated figures cap |
| `MAX_VIDEOS` | *(all)* | scope cap for testing |
| `QA_MAX_ITERATIONS` | `3` | critic/refiner loop bound |
| `COMPILE_LATEX` | `true` | set false without pdflatex |

Credentials: `GOOGLE_API_KEY` (AI Studio) **or** Vertex AI
(`GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`).

## Tests & eval

```bash
pytest                                                      # unit tests (no network, no API key needed)
adk eval bookforge eval/bookforge.evalset.json             # smoke evals (2 cases, ~2-5 min)
adk eval bookforge eval/bookforge-comprehensive.evalset.json  # full suite (30+ cases, ~30-60 min)
```

See [`eval/README.md`](eval/README.md) for detailed evaluation guide, test categories, and performance benchmarks.

## Deployment

See [`deployment/README.md`](deployment/README.md): Dockerfile (Python + ffmpeg
+ TeX Live), **Cloud Run Job** recipe (recommended — long-running batch,
scale-to-zero billing, Secret Manager for the API key) and the Vertex AI Agent
Engine alternative (`adk deploy agent_engine`).

## Legal / responsible use

Downloading and transcoding YouTube content is subject to YouTube's Terms of
Service and copyright law. Run BookForge only against content you own or have
permission to use (your own channel, licensed material). The generated book
reproduces frames and derived text from the videos.

## Pre-flight checks

BookForge validates the environment before running:
- ✅ Gemini credentials (`GOOGLE_API_KEY` or Vertex AI)
- ✅ `ffmpeg` availability (warns if missing)
- ✅ `pdflatex` availability (auto-disables PDF compilation if missing)

If a required credential is missing, the pipeline fails fast with a clear
error message.

## Project layout

```
bookforge/
├── agent.py            # root_agent for `adk run` / `adk web`
├── main.py             # CLI runner (python -m bookforge.main <url>)
├── docker_entry.py     # Docker CHANNEL_URL entrypoint
├── config.py           # env-driven Settings + structured logging
├── schemas.py          # pydantic contracts (manifest, analysis, assets)
├── prompts.py          # brace-free instruction templates
├── agents/             # intake · media · analyst · assets · writer · critic · compiler · orchestrator
└── tools/              # workspace · youtube · frames · latex
tests/                  # offline unit tests (49 tests)
├── conftest.py         # shared fixtures
├── test_imports.py     # import chain smoke tests
├── test_schemas.py     # schema validation tests
├── test_graph.py       # agent graph wiring tests
├── test_frames.py      # frame dedupe tests
├── test_latex.py       # LaTeX rendering tests
├── test_workspace.py   # workspace management tests
└── test_youtube.py     # VTT parsing tests
eval/                   # ADK eval set
deployment/             # Docker + Cloud Run Job / Agent Engine guides
```
