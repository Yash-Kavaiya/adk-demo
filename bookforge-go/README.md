# BookForge Go Agent

Go implementation of BookForge using Google ADK Go v2.0 - a multi-agent system that transforms YouTube channels into compiled LaTeX books.

## Overview

This is a **Go port** of the original Python BookForge agent, maintaining the same architecture and workflow:

```
bookforge (Sequential Workflow)
├── ChannelIntakeAgent        → channel URL -> manifest/videos.json
├── BookProductionAgent        → loop over pending videos
│   └── chapter_pipeline (Sequential)
│       ├── MediaAcquisitionAgent    → download, transcribe, extract frames
│       ├── TranscriptAnalystAgent   → structured analysis (JSON)
│       ├── VisualAssetAgent        → render charts, tables, figures
│       ├── ChapterWriterAgent      → LaTeX chapter body
│       └── chapter_qa_loop (Loop)
│           ├── ChapterCriticAgent  → compile + verify
│           └── ChapterRefinerAgent → fix defects
└── BookCompilerAgent         → main.tex + pdflatex -> book.pdf
```

## Prerequisites

- **Go 1.23+** (required)
- **Google ADK Go v2.0.0+** (required)
- **ffmpeg** (optional, for frame extraction)
- **pdflatex** (optional, for PDF compilation)
- **Google API Key** (required for Gemini models)

## Quick Start

### 1. Install Dependencies

```bash
cd bookforge-go

# Initialize Go module and fetch dependencies
go mod tidy
```

### 2. Set API Key

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```bash
GOOGLE_API_KEY=your-actual-api-key-here
```

Get your API key from: https://aistudio.google.com/app/apikey

### 3. Run the Agent

**Command-line interface:**

```bash
# Load environment variables (Windows)
.\env.bat

# Load environment variables (Unix/Mac)
source .env

# Run the agent
go run agent.go
```

Then paste a YouTube channel URL when prompted.

**Web interface:**

```bash
go run agent.go web api webui
```

Open http://localhost:8080 in your browser.

## Architecture

### Agents

1. **ChannelIntakeAgent** - Extracts channel metadata and video list
2. **MediaAcquisitionAgent** - Downloads video, transcript, frames
3. **TranscriptAnalystAgent** - Analyzes transcript into structured data
4. **VisualAssetAgent** - Renders charts, tables, curated frames
5. **ChapterWriterAgent** - Generates LaTeX chapter body
6. **ChapterCriticAgent** - Compiles and verifies chapter
7. **ChapterRefinerAgent** - Fixes defects from critic
8. **BookCompilerAgent** - Assembles and compiles final book

### Workflows

- **Sequential Workflow** - Main pipeline (intake → production → compilation)
- **Loop Workflow** - QA loop (critic ↔ refiner, max 3 iterations)
- **Production Loop** - Per-video chapter processing with checkpointing

## Configuration

Environment variables (prefix: `BOOKFORGE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | *(required)* | Gemini API key |
| `BOOKFORGE_WORKSPACE_ROOT` | `data` | Output directory |
| `BOOKFORGE_MAX_VIDEOS` | `0` (all) | Cap video count |
| `BOOKFORGE_COMPILE_LATEX` | `true` | Enable PDF compilation |
| `BOOKFORGE_FRAME_INTERVAL_SEC` | `5` | Frame extraction rate |
| `BOOKFORGE_MAX_FRAMES_PER_CHAPTER` | `12` | Max figures per chapter |

## Project Structure

```
bookforge-go/
├── agent.go              # Main agent implementation
├── go.mod                # Go module definition
├── go.sum                # Dependency checksums (generated)
├── .env.example          # Environment template
├── .env                  # Your local config (gitignored)
├── tools/                # Tool implementations (TODO)
│   ├── youtube.go        # YouTube download & transcription
│   ├── frames.go         # Frame extraction & deduplication
│   ├── latex.go          # LaTeX rendering & compilation
│   └── workspace.go      # Workspace & manifest management
└── README.md             # This file
```

## Implementation Status

### ✅ Completed

- [x] Main agent structure and workflow
- [x] All 8 agent definitions
- [x] Sequential workflow configuration
- [x] Go module setup
- [x] Configuration system
- [x] Documentation

### 🚧 In Progress

- [ ] YouTube listing tool
- [ ] Video download tool
- [ ] Transcript extraction (captions/whisper)
- [ ] Frame extraction & perceptual hashing
- [ ] Chart rendering (Go plotting library)
- [ ] Table rendering (LaTeX generation)
- [ ] LaTeX compilation tool
- [ ] Workspace & manifest management
- [ ] Loop workflow for QA
- [ ] Production loop with checkpointing

### 📋 Planned

- [ ] Error handling & recovery
- [ ] Resume from checkpoint
- [ ] Parallel processing options
- [ ] Testing suite
- [ ] CLI flags and options
- [ ] Docker containerization
- [ ] Cloud deployment guides

## Differences from Python Version

### Advantages of Go Implementation

1. **Performance** - Compiled binary, faster startup
2. **Concurrency** - Native goroutines for parallel processing
3. **Type Safety** - Compile-time type checking
4. **Deployment** - Single binary, no Python dependencies
5. **Memory** - Lower memory footprint

### Current Limitations

1. **Tools** - Not all tools implemented yet (YouTube, ffmpeg, LaTeX)
2. **Libraries** - Need Go equivalents for Python libraries (yt-dlp, whisper, matplotlib)
3. **Testing** - Test suite not yet ported

## Development

### Build

```bash
go build -o bookforge agent.go
```

### Test

```bash
go test ./...
```

### Format

```bash
go fmt ./...
```

## Dependencies

Core ADK Go v2.0 packages:

- `google.golang.org/adk/v2/agent` - Agent abstractions
- `google.golang.org/adk/v2/agent/llmagent` - LLM-backed agents
- `google.golang.org/adk/v2/agent/workflowagent` - Workflow orchestration
- `google.golang.org/adk/v2/tool` - Tool definitions
- `google.golang.org/adk/v2/model/gemini` - Gemini model integration
- `google.golang.org/genai` - Google Gen AI SDK

Additional (planned):

- YouTube download: TBD (Go equivalent of yt-dlp)
- Audio processing: TBD (Go equivalent of faster-whisper)
- Image processing: `github.com/disintegration/imaging`
- PDF generation: `github.com/signintech/gopdf`
- Plotting: `gonum.org/v1/plot`

## Troubleshooting

### API Key Issues

```
Error: GOOGLE_API_KEY environment variable must be set
```

**Solution:** Create `.env` file with your API key or set environment variable.

### Go Module Issues

```
Error: cannot find package
```

**Solution:** Run `go mod tidy` to download dependencies.

### ADK Version Issues

```
Error: incompatible version
```

**Solution:** Ensure ADK Go v2.0.0+ is installed: `go get -u google.golang.org/adk/v2`

## Comparison with Python Version

| Aspect | Python | Go |
|--------|--------|-----|
| Language | Python 3.10+ | Go 1.23+ |
| ADK Version | ADK Python 2.x | ADK Go 2.0+ |
| Runtime | Interpreted | Compiled |
| Package Manager | pip/uv | go modules |
| Concurrency | asyncio | goroutines |
| Type System | Dynamic + type hints | Static typing |
| Deployment | Python + deps | Single binary |
| Memory | Higher | Lower |
| Startup | Slower | Faster |
| Status | Complete | In Progress |

## Contributing

This is a work-in-progress port. Contributions welcome:

1. Implement missing tools (YouTube, ffmpeg wrappers)
2. Add error handling
3. Port test suite
4. Add logging and observability
5. Optimize performance

## License

Same as the original BookForge Python implementation.

## References

- **ADK Go Documentation:** https://google.github.io/adk-docs/get-started/go/
- **ADK Go GitHub:** https://github.com/google/adk-go
- **Original Python Implementation:** ../bookforge/
- **Gemini API:** https://ai.google.dev/docs
