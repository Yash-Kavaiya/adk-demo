# BookForge — YouTube Channel → Book, as a Google ADK Multi-Agent System

**Input:** a YouTube channel URL.
**Output:** a compiled, print-ready PDF book (`book.pdf`) plus a full LaTeX
source tree — one chapter per video, with study notes, tables, charts,
diagrams, curated screenshots, glossary and exercises.

Built on [Google ADK](https://adk.dev/) (Python). The graph mixes
deterministic agents (download, frames, rendering, compiling — no tokens
wasted) with LLM agents (analysis, writing, critique) where judgment is
needed.

---

## 1. Your flow → enhanced flow

| Your step | Enhancement in this design |
|---|---|
| Fetch all video links → `.json` | `.json` becomes a **versioned manifest** with per-video status (`pending → media → analyzed → written → verified / failed`). Runs are **resumable**: a crash or quota error on video 37 of 200 restarts exactly there. |
| Download entire video | Download at capped resolution (480p default) — plenty for screenshots, ~10× smaller/faster. Audio extracted once for transcription fallback. |
| Fetch audio transcript | **Captions first** (free, timestamp-aligned via `yt-dlp`), **faster-whisper local fallback** when captions are absent. Timestamps are kept so figures can cite the exact moment they came from. |
| Screenshot every 5 s, remove duplicates | Every-N-seconds extraction + **perceptual-hash dedupe** (hamming distance) + **blur/darkness rejection**, then spread-curation keeps at most K frames per chapter. |
| Generate diagrams / tables / charts | A **Transcript Analyst** LLM first emits a *validated JSON analysis* (concepts, table specs, chart specs with real data, diagram specs, glossary, quiz). **Charts are rendered deterministically by matplotlib from the spec data** (never hand-drawn by the LLM), tables become `booktabs` fragments, diagrams become TikZ. |
| Create enhanced chapter `.tex` | Chapter Writer composes the chapter from analysis + asset manifest only — it cannot invent figures that don't exist. |
| Verify `.tex`, refine loop | Bounded `LoopAgent` (max 3): **Critic actually compiles the chapter with pdflatex** and checks every referenced figure/table exists, then `approve_chapter` (escalate) or emits a structured critique the Refiner consumes. |
| Compile all `.tex` into a book | Book Compiler builds shared preamble, title page, TOC, glossary, per-chapter `\input`, runs pdflatex (2 passes), parses the log, and publishes `book.pdf` + `manifest.json`. |
| *(not in your flow)* | **Production layer:** env-based config, structured logging, per-video error isolation, unit tests, eval set, Dockerfile, Cloud Run Job / Agent Engine deployment. |

## 2. Agent graph (ADK)

```
root_agent  (SequentialAgent "bookforge")
├── ChannelIntakeAgent            BaseAgent   channel URL → manifest/videos.json
├── BookProductionAgent           BaseAgent   resumable loop over manifest
│   └── chapter_pipeline          SequentialAgent        (run once per video)
│       ├── MediaAcquisitionAgent BaseAgent   download, transcript, curated frames
│       ├── TranscriptAnalystAgent LlmAgent   transcript → ChapterAnalysis JSON
│       ├── VisualAssetAgent      BaseAgent   charts (matplotlib), tables, figures
│       ├── ChapterWriterAgent    LlmAgent    → chapter.tex  (output_key)
│       └── chapter_qa_loop       LoopAgent (max_iterations=3)
│           ├── ChapterCriticAgent  LlmAgent  tools: compile_chapter, approve_chapter
│           └── ChapterRefinerAgent LlmAgent  rewrite using critique
└── BookCompilerAgent             BaseAgent   main.tex + pdflatex → book.pdf
```

**Why custom `BaseAgent`s for the loop/media/compile stages?** They are
deterministic engineering steps (yt-dlp, ffmpeg, matplotlib, pdflatex).
Making them LLM tool-calls would burn tokens, add flakiness, and make
retries unpredictable. LLM agents are used exactly where language judgment
is required: analyze, write, critique, refine.

## 3. State & artifacts

Session state keys (small JSON only — big content lives on disk):

| Key | Producer | Consumer |
|---|---|---|
| `channel_url`, `channel_slug` | Intake | all |
| `videos` (manifest summary) | Intake | Production loop, Compiler |
| `current_video` | Production loop | pipeline stages |
| `transcript` | Media | Analyst (templated into instruction) |
| `analysis_json` | Analyst (`output_schema`) | Assets, Writer |
| `assets_manifest` | Assets | Writer, Critic |
| `chapter_tex` | Writer / Refiner | Critic, Orchestrator |
| `critique` | Critic | Refiner |
| `qa_verdict` | Critic | Orchestrator (chapter status) |
| `book_pdf` | Compiler | final response |

On-disk workspace (`data/<channel_slug>/`):

```
manifest.json                 # videos + per-video status (resume source of truth)
videos/<video_id>/video.mp4, audio.wav, transcript.txt, frames_raw/, frames/
chapters/<NN>_<slug>/chapter.tex, figures/, tables/
build/                        # pdflatex scratch
book/book.pdf, main.tex, preamble.tex
```

## 4. Reliability semantics

- **Checkpoint:** after every video, `manifest.json` is rewritten atomically.
- **Error isolation:** any exception inside a video's pipeline marks that video
  `failed` (with the error), the loop continues.
- **Idempotency:** completed stages are skipped on re-run (file existence +
  status), so re-running is cheap.
- **Bounded refinement:** QA loop caps at 3 iterations; a chapter that never
  passes is saved as `written` with a warning, never silently dropped.

## 5. Build plan

1. Plan & architecture docs (this file, `solution-architecture.md`).
2. Config / schemas / prompts.
3. Tools: `workspace`, `youtube`, `frames`, `latex`.
4. Agents: intake → media → analyst → assets → writer → critic loop → compiler → orchestrator.
5. Entry points: `bookforge/agent.py` (`adk run` / `adk web`), `python -m bookforge.main` CLI.
6. Tests, eval set, Dockerfile, deployment docs, README.
7. Validation: `pytest`, import smoke test, agent-graph construction test.

## 5a. ADK Migration Notes

- **SequentialAgent/LoopAgent deprecation:** ADK ≥2.0 deprecates these in
  favor of graph-based `Workflow`. However, `Workflow` cannot yet be used as
  an `LlmAgent` sub-agent. Since BookForge's pipeline mixes LLM and code
  agents within sequential/loop structures, we continue using the legacy
  agents until `Workflow` gains full sub-agent support.
- **Suppression:** deprecation warnings are documented and acknowledged.
- **Future migration:** when `Workflow` supports nested LlmAgent composition,
  replace `SequentialAgent` → `Workflow(edges=[...])` and `LoopAgent` →
  `Workflow` with conditional loop edges.

## 6. Decisions worth knowing

- **Models:** analyst/critic default `gemini-2.5-flash` (fast, cheap);
  writer defaults `gemini-2.5-pro` (long-form quality). All overridable by env.
- **LaTeX:** chapters are preamble-free bodies; the book owns the single
  preamble → chapters are compilable standalone *and* as part of the book.
- **Diagrams:** TikZ generated by the writer from the analyst's diagram spec;
  the QA compile catches TikZ errors and the refiner repairs them.
- **YouTube ToS / copyright:** this tool processes content you have rights to
  (your own channel, licensed, or with permission). Documented in README.
