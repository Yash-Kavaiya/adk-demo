# BookForge Improvement Action Plan

Based on the comprehensive codebase review, here are prioritized actions to improve code quality and best practices.

---

## 🔴 Critical Priority (Do Immediately)

### 1. Add Go Tests
**Impact:** High | **Effort:** Medium | **Timeline:** 2-3 days

Create test files for Go implementation:

```bash
# Create test structure
touch bookforge-go/agent_test.go
touch bookforge-go/tools/workspace_test.go
touch bookforge-go/tools/schemas_test.go
```

**Example tests needed:**
```go
// agent_test.go
func TestIntakeAgentIsDeterministic(t *testing.T)
func TestAnalystAgentUsesLLM(t *testing.T)
func TestWorkflowStructureMatchesPython(t *testing.T)

// tools/workspace_test.go
func TestManifestRoundtrip(t *testing.T)
func TestPendingVideosFilter(t *testing.T)
func TestSlugify(t *testing.T)
```

### 2. Add Python Integration Tests
**Impact:** High | **Effort:** Medium | **Timeline:** 1-2 days

```python
# tests/test_integration.py
@pytest.mark.integration
async def test_single_video_workflow():
    """End-to-end test with mocked YouTube API"""
    pass

@pytest.mark.integration
async def test_resume_after_failure():
    """Test resumability with failed video"""
    pass
```

---

## 🟡 High Priority (Next Sprint)

### 3. Extract Magic Strings to Constants
**Impact:** Medium | **Effort:** Low | **Timeline:** 2 hours

```python
# bookforge/constants.py
from typing import Final

# Status constants
TERMINAL_STATUSES: Final = frozenset(["verified", "failed"])
PENDING_STATUSES: Final = frozenset(["pending", "media", "analyzed", "assets", "written"])

# Media defaults
DEFAULT_FRAME_INTERVAL: Final = 5
DEFAULT_FRAME_THRESHOLD: Final = 6
MAX_FRAMES_PER_CHAPTER: Final = 12

# QA Loop
DEFAULT_QA_ITERATIONS: Final = 3

# File patterns
MANIFEST_FILENAME: Final = "manifest.json"
CHAPTER_FILENAME: Final = "chapter.tex"
```

**Usage:**
```python
# Before
if v.status not in ("verified",)

# After
from bookforge.constants import TERMINAL_STATUSES
if v.status in TERMINAL_STATUSES
```

### 4. Add Rate Limiting to API Calls
**Impact:** High | **Effort:** Low | **Timeline:** 3 hours

```python
# bookforge/utils/rate_limit.py
from functools import wraps
import time
from threading import Lock

class RateLimiter:
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.timestamps: list[float] = []
        self.lock = Lock()
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()
                # Remove old timestamps
                self.timestamps = [t for t in self.timestamps if now - t < self.period]
                
                if len(self.timestamps) >= self.calls:
                    sleep_time = self.period - (now - self.timestamps[0])
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
                result = func(*args, **kwargs)
                self.timestamps.append(time.time())
                return result
        return wrapper

# Usage
youtube_rate_limit = RateLimiter(calls=10, period=1.0)  # 10 calls/sec
gemini_rate_limit = RateLimiter(calls=2, period=1.0)    # 2 calls/sec

@youtube_rate_limit
def list_channel_videos(channel_url: str):
    ...

@gemini_rate_limit
async def analyze_transcript(transcript: str):
    ...
```

### 5. Add Input Validation
**Impact:** Medium | **Effort:** Low | **Timeline:** 2 hours

```python
# bookforge/utils/validation.py
import re
from urllib.parse import urlparse

def validate_youtube_url(url: str) -> str:
    """Validate and normalize YouTube URL."""
    parsed = urlparse(url)
    if parsed.netloc not in ("youtube.com", "www.youtube.com", "youtu.be"):
        raise ValueError(f"Invalid YouTube URL: {url}")
    return url

def validate_video_id(video_id: str) -> str:
    """Validate YouTube video ID format."""
    if not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        raise ValueError(f"Invalid video ID: {video_id}")
    return video_id

def validate_file_size(path: Path, max_bytes: int = 2 * 1024**3) -> Path:
    """Validate file size doesn't exceed limit."""
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"File too large: {size} bytes (max {max_bytes})")
    return path
```

---

## 🟢 Medium Priority (This Month)

### 6. Improve Go Dependency Injection
**Impact:** Medium | **Effort:** Medium | **Timeline:** 1 day

```go
// Current: Constructor with no dependencies
func NewIntakeAgent() *IntakeAgent {
    return &IntakeAgent{}
}

// Better: Inject dependencies
type IntakeAgent struct {
    cfg *Config
    ws  *Workspace
    yt  *YouTubeClient
}

func NewIntakeAgent(cfg *Config, ws *Workspace, yt *YouTubeClient) *IntakeAgent {
    return &IntakeAgent{cfg: cfg, ws: ws, yt: yt}
}

func (a *IntakeAgent) Run(ctx context.Context, req agent.Request) (agent.Response, error) {
    // Use injected dependencies
    videos, err := a.yt.ListChannelVideos(ctx, channelURL)
    // ...
}
```

### 7. Add Go Configuration from Environment
**Impact:** Medium | **Effort:** Low | **Timeline:** 3 hours

```go
// bookforge-go/config.go
package main

import (
    "fmt"
    "os"
    "strconv"
)

func LoadConfigFromEnv() (*Config, error) {
    cfg := DefaultConfig()
    
    if val := os.Getenv("BOOKFORGE_ANALYST_MODEL"); val != "" {
        cfg.AnalystModel = val
    }
    if val := os.Getenv("BOOKFORGE_WRITER_MODEL"); val != "" {
        cfg.WriterModel = val
    }
    if val := os.Getenv("BOOKFORGE_MAX_VIDEOS"); val != "" {
        maxVids, err := strconv.Atoi(val)
        if err != nil {
            return nil, fmt.Errorf("invalid BOOKFORGE_MAX_VIDEOS: %w", err)
        }
        cfg.MaxVideos = maxVids
    }
    if val := os.Getenv("BOOKFORGE_COMPILE_LATEX"); val != "" {
        cfg.CompileLaTeX = val == "true" || val == "1"
    }
    
    if err := cfg.Validate(); err != nil {
        return nil, err
    }
    
    return cfg, nil
}

func (c *Config) Validate() error {
    if c.WorkspaceRoot == "" {
        return errors.New("workspace_root cannot be empty")
    }
    if c.AnalystModel == "" {
        return errors.New("analyst_model cannot be empty")
    }
    return nil
}
```

### 8. Add Package Documentation
**Impact:** Low | **Effort:** Low | **Timeline:** 2 hours

```go
// bookforge-go/agent.go
// Package main implements BookForge, a multi-agent system that converts
// YouTube educational video channels into professionally typeset LaTeX books.
//
// Architecture:
//
// The system uses a hybrid agent architecture:
//   - Deterministic agents (custom structs) handle media processing, asset
//     generation, and compilation
//   - LLM agents (llmagent.New) handle content analysis, writing, and review
//
// Workflow:
//
//  1. IntakeAgent: Lists channel videos, creates manifest
//  2. ProductionAgent: Loops over pending videos
//     a. MediaAgent: Downloads video, extracts transcript and frames
//     b. AnalystAgent: AI-powered analysis of transcript
//     c. AssetsAgent: Renders charts, tables, curates frames
//     d. WriterAgent: AI-powered LaTeX chapter composition
//     e. CriticAgent & RefinerAgent: QA loop with AI review
//  3. CompilerAgent: Assembles and compiles final book PDF
//
// Resume Logic:
//
// The manifest tracks per-video status (pending/media/analyzed/assets/
// written/verified/failed). Re-running skips already-verified chapters.
//
// Usage:
//
//  adk run bookforge
//  # or
//  go run . <channel-url>
package main

// tools/workspace.go
// Package tools provides filesystem workspace management, external tool
// integrations (YouTube API, ffmpeg, whisper, pdflatex), and data schemas
// for the BookForge multi-agent system.
//
// Workspace Structure:
//
//  data/<channel-slug>/
//    manifest.json                  # Per-video processing status
//    videos/<video-id>/             # Raw downloads
//      video.mp4, audio.wav, transcript.txt, media.json
//      frames_raw/, frames/
//    chapters/<NN>_<slug>/          # Generated chapters
//      chapter.tex, figures/, tables/
//    book/                          # Final output
//      main.tex, preamble.tex, book.pdf
//
// The Workspace struct encapsulates all filesystem operations and provides
// manifest CRUD, atomic file writes, and path management.
package tools
```

---

## 🔵 Low Priority (Nice to Have)

### 9. Add Performance Monitoring
**Impact:** Low | **Effort:** Medium | **Timeline:** 1 day

```python
# bookforge/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Metrics
videos_processed = Counter(
    'bookforge_videos_processed_total',
    'Total videos processed',
    ['status']  # labels: success, failed
)

video_processing_duration = Histogram(
    'bookforge_video_processing_seconds',
    'Time to process one video',
    buckets=[60, 300, 600, 1800, 3600]  # 1m, 5m, 10m, 30m, 1h
)

active_videos = Gauge(
    'bookforge_active_videos',
    'Number of videos currently processing'
)

llm_calls = Counter(
    'bookforge_llm_calls_total',
    'Total LLM API calls',
    ['agent', 'model']
)

# Decorator
def track_duration(metric: Histogram):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.observe(duration)
        return wrapper
    return decorator

# Usage
@track_duration(video_processing_duration)
async def process_video(video_id: str):
    active_videos.inc()
    try:
        # Process...
        videos_processed.labels(status='success').inc()
    except Exception:
        videos_processed.labels(status='failed').inc()
        raise
    finally:
        active_videos.dec()
```

### 10. Add CLI Progress Bars
**Impact:** Low | **Effort:** Low | **Timeline:** 2 hours

```python
# bookforge/utils/progress.py
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

console = Console()

def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False
    )

# Usage in orchestrator
async def _run_async_impl(self, ctx: InvocationContext):
    pending = ws.pending_videos()
    
    with create_progress() as progress:
        task = progress.add_task(
            f"Processing {len(pending)} videos",
            total=len(pending)
        )
        
        for i, record in enumerate(pending):
            progress.update(
                task,
                description=f"Video {i+1}/{len(pending)}: {record.title[:40]}",
                completed=i
            )
            # Process video...
            progress.update(task, advance=1)
```

---

## Implementation Timeline

### Week 1 (Critical Priority)
- **Day 1-2:** Go unit tests (agent_test.go, workspace_test.go)
- **Day 3:** Python integration tests
- **Day 4:** Rate limiting implementation
- **Day 5:** Input validation

### Week 2 (High Priority)
- **Day 1:** Extract magic strings
- **Day 2:** Go dependency injection
- **Day 3:** Go config from env
- **Day 4-5:** Package documentation

### Week 3+ (Medium/Low Priority)
- Performance monitoring (if needed)
- CLI UX improvements (if needed)
- Additional optimizations based on profiling

---

## Testing the Improvements

### After Each Change

```bash
# Python
pytest -v
python -m bookforge.main --max-videos 1 <test-channel>

# Go
go test ./...
go run . <test-channel>
```

### Integration Testing

```bash
# Full workflow test
adk eval bookforge eval/bookforge.evalset.json
adk eval bookforge eval/bookforge-comprehensive.evalset.json
```

---

## Success Metrics

Track improvements with:

1. **Test Coverage**
   - Python: Maintain >80% coverage
   - Go: Achieve >70% coverage

2. **Code Quality**
   - Ruff: 0 violations
   - Go vet: 0 issues
   - Go staticcheck: 0 issues

3. **Performance**
   - Video processing time (target: <5min avg)
   - Frame deduplication efficiency
   - LLM token usage

4. **Reliability**
   - Success rate on varied channels
   - Resume success rate
   - Error recovery rate

---

## Quick Wins (Can Do Today)

1. **Extract constants** (30 min)
2. **Add input validation** (1 hour)
3. **Add package docs to Go** (1 hour)
4. **Create Python constants.py** (30 min)

These quick wins improve code quality with minimal effort.

---

## Review Schedule

- **Weekly:** Review test coverage and metrics
- **Monthly:** Full code quality audit
- **Quarterly:** Architecture review

---

**Action Plan Complete** ✅

Start with Critical Priority items and work through the list systematically. Each improvement builds on the previous ones and maintains the excellent foundation already in place.
