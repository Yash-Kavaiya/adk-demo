# BookForge Evaluation Sets

This directory contains evaluation sets for testing the BookForge multi-agent pipeline.

## Available Evaluation Sets

### 1. `bookforge.evalset.json` (Smoke Tests)
**Purpose:** Quick validation of core functionality  
**Test Count:** 2 cases  
**Runtime:** ~2-5 minutes  
**Requirements:**
- Network access to YouTube
- Valid `GOOGLE_API_KEY` or Vertex AI credentials

**Usage:**
```bash
adk eval bookforge eval/bookforge.evalset.json
```

### 2. `bookforge-comprehensive.evalset.json` (Full Suite)
**Purpose:** Comprehensive validation of all agents and workflows  
**Test Count:** 30+ cases covering:
- Channel intake (3 cases)
- Media acquisition (4 cases)
- Transcript analysis (3 cases)
- Asset generation (3 cases)
- Chapter writing (2 cases)
- QA loop (3 cases)
- Book compilation (2 cases)
- End-to-end workflows (3 cases)
- Orchestration (2 cases)
- Configuration (2 cases)

**Runtime:** ~30-60 minutes (depending on network and LLM latency)  
**Requirements:**
- Network access to YouTube
- Valid `GOOGLE_API_KEY` or `OPENAI_API_KEY` (for NVIDIA NIM models)
- `ffmpeg` on PATH (for frame extraction)
- `pdflatex` on PATH (optional, for compile tests)

**Usage:**
```bash
# Run all tests
adk eval bookforge eval/bookforge-comprehensive.evalset.json

# Run with verbose output
adk eval bookforge eval/bookforge-comprehensive.evalset.json --verbose

# Run specific eval cases (filter by ID prefix)
adk eval bookforge eval/bookforge-comprehensive.evalset.json --filter intake_
adk eval bookforge eval/bookforge-comprehensive.evalset.json --filter e2e_
```

## Test Categories

### Intake Tests (`intake_*`)
Validate channel URL extraction, video discovery, and manifest management:
- Error handling for missing URLs
- Channel metadata extraction
- Resume from existing manifest

### Media Tests (`media_*`)
Validate video download, transcription, and frame extraction:
- Video download at capped resolution
- Caption extraction (YouTube native)
- Whisper fallback for videos without captions
- Frame deduplication using perceptual hashing

### Analyst Tests (`analyst_*`)
Validate structured analysis from transcripts:
- ChapterAnalysis JSON schema compliance
- Table extraction from tabular data
- Chart data extraction from numeric content

### Assets Tests (`assets_*`)
Validate deterministic asset rendering:
- Booktabs table fragment generation
- Matplotlib chart rendering to PDF
- Frame curation across video timeline

### Writer Tests (`writer_*`)
Validate LaTeX chapter generation:
- Valid chapter structure
- Asset reference validation (no invented filenames)

### Critic Tests (`critic_*`)
Validate compile-time verification:
- pdflatex compilation check
- Missing asset detection
- Chapter approval workflow

### Refiner Tests (`refiner_*`)
Validate defect correction:
- Critic feedback incorporation
- Preservation of valid content

### Compiler Tests (`compiler_*`)
Validate final book assembly:
- main.tex generation
- Failed chapter exclusion

### End-to-End Tests (`e2e_*`)
Validate complete workflows:
- Single video channel processing
- Multi-video resume from checkpoint
- MAX_VIDEOS limit enforcement

### Orchestration Tests (`orchestration_*`)
Validate agent coordination:
- Error isolation (one failed chapter doesn't block the book)
- QA loop iteration limits

### Configuration Tests (`config_*`)
Validate settings and model routing:
- NVIDIA NIM endpoint configuration
- COMPILE_LATEX=false mode

## Running Tests in CI/CD

### Prerequisites Setup
```bash
# Install dependencies
pip install -e ".[dev]"

# Set credentials (choose one)
export GOOGLE_API_KEY="your-google-api-key"
# OR for NVIDIA NIM
export BOOKFORGE_OPENAI_API_KEY="your-nvidia-api-key"
export BOOKFORGE_OPENAI_API_BASE="https://integrate.api.nvidia.com/v1"

# Optional: set test channel
export TEST_CHANNEL_URL="https://www.youtube.com/@your-test-channel"
```

### Run Tests
```bash
# Smoke test (fast)
adk eval bookforge eval/bookforge.evalset.json

# Full suite
adk eval bookforge eval/bookforge-comprehensive.evalset.json

# Parallel execution (if supported by adk)
adk eval bookforge eval/bookforge-comprehensive.evalset.json --parallel 4
```

### Expected Outcomes

**Pass Criteria:**
- All `final_response` text patterns match
- No unhandled exceptions
- Session state updates correctly

**Failure Investigation:**
```bash
# Check logs
cat ~/.adk/logs/bookforge-eval-*.log

# Inspect workspace artifacts
ls -R data/

# Review specific chapter
cat data/<channel-slug>/chapters/01_*/chapter.tex
```

## Writing Custom Eval Cases

Each eval case follows this structure:

```json
{
  "eval_id": "unique_identifier",
  "description": "Human-readable description",
  "conversation": [
    {
      "invocation_id": "inv-1",
      "user_content": {
        "parts": [{ "text": "user message" }],
        "role": "user"
      },
      "final_response": {
        "parts": [{ "text": "expected substring in response" }],
        "role": "model"
      }
    }
  ],
  "session_input": {
    "app_name": "bookforge",
    "user_id": "eval-user",
    "state": {
      "key": "pre-populated state for this test"
    }
  }
}
```

**Tips:**
- Use descriptive `eval_id` with category prefix
- Pre-populate `state` to test specific agents in isolation
- `final_response.parts[0].text` matches as substring (not exact match)
- Chain multiple invocations to test multi-turn workflows

## Performance Benchmarks

Typical execution times on standard hardware:

| Test Category | Count | Time (avg) |
|---------------|-------|------------|
| Intake        | 3     | 10-30s     |
| Media         | 4     | 2-5 min    |
| Analyst       | 3     | 1-3 min    |
| Assets        | 3     | 30-60s     |
| Writer        | 2     | 2-4 min    |
| Critic        | 3     | 1-3 min    |
| Refiner       | 1     | 2-4 min    |
| Compiler      | 2     | 30-90s     |
| E2E           | 3     | 10-30 min  |
| Orchestration | 2     | 5-15 min   |
| Config        | 2     | 30s-2 min  |

**Total Comprehensive Suite:** ~30-60 minutes

## Troubleshooting

### Common Issues

**YouTube rate limiting:**
```
Error: HTTP 429 Too Many Requests
```
**Solution:** Add delays between tests or use a dedicated test channel with few videos.

**Missing ffmpeg:**
```
ffmpeg not found on PATH
```
**Solution:** Install ffmpeg: https://ffmpeg.org/download.html

**pdflatex unavailable:**
```
pdflatex not found
```
**Solution:** Install TeX Live or MiKTeX, or run with `BOOKFORGE_COMPILE_LATEX=false`

**API quota exceeded:**
```
Error: 429 quota exceeded
```
**Solution:** Use a different API key or wait for quota reset

**Network timeouts:**
```
Error: Connection timeout
```
**Solution:** Increase timeout or use cached test data

## Extending the Test Suite

To add new test cases:

1. Identify the agent/workflow to test
2. Choose appropriate `eval_id` prefix
3. Define minimal `session_input.state` for the scenario
4. Specify expected `final_response` substring
5. Add to `eval_cases` array in the appropriate eval set

Example:
```json
{
  "eval_id": "writer_03_tikz_diagrams",
  "description": "Verify writer renders TikZ diagrams from analysis",
  "conversation": [
    {
      "invocation_id": "inv-writer-03",
      "user_content": {
        "parts": [{ "text": "Write chapter with diagram" }],
        "role": "user"
      },
      "final_response": {
        "parts": [{ "text": "\\begin{tikzpicture}" }],
        "role": "model"
      }
    }
  ],
  "session_input": {
    "app_name": "bookforge",
    "user_id": "eval-writer-tikz",
    "state": {
      "video_title": "Diagram Chapter",
      "analysis_json": "{...with diagrams...}",
      "assets_manifest": "{...}",
      "current_video": {...},
      "channel_slug": "test-channel"
    }
  }
}
```

## Reporting Issues

When reporting test failures, include:
1. Eval set and case ID
2. Full error message and stack trace
3. Environment info (OS, Python version, adk version)
4. Relevant logs from `~/.adk/logs/`
5. Workspace artifacts (if applicable)

Submit issues at: https://github.com/your-org/bookforge/issues
