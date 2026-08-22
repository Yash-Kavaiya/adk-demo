# Parallelization Quick Reference

## Decision Matrix: What to Parallelize?

```
┌─────────────────────────┬────────────┬───────────┬──────────┬──────────────┐
│ Component               │ Parallelize│ Speedup   │ Risk     │ Recommended  │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────────┤
│ Root Pipeline           │    ❌      │    N/A    │   High   │   NEVER      │
│ (Intake→Prod→Compile)   │            │           │          │              │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────────┤
│ Video Processing Loop   │    ✅      │   2-3x    │  Medium  │   YES (2-3)  │
│ (ProductionAgent)       │            │           │          │   concurrent │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────────┤
│ Chapter Pipeline        │    ❌      │    N/A    │   High   │   NEVER      │
│ (Media→Analyst→Writer)  │            │           │          │              │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────────┤
│ Frame Extraction        │    ✅      │   2-4x    │    Low   │   YES (4     │
│ (FFmpeg calls)          │            │           │          │   workers)   │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────────┤
│ Asset Rendering         │    🟡      │  1.2-1.5x │    Low   │   MAYBE      │
│ (Charts/Tables)         │            │           │          │   (if many)  │
├─────────────────────────┼────────────┼───────────┼──────────┼──────────────┤
│ QA Loop                 │    ❌      │    N/A    │   High   │   NEVER      │
│ (Critic→Refiner)        │            │           │          │              │
└─────────────────────────┴────────────┴───────────┴──────────┴──────────────┘
```

## Data Flow Dependencies (MUST BE SEQUENTIAL)

```
┌──────────────┐
│ IntakeAgent  │  Creates manifest.json
└──────┬───────┘
       │ ⚠️ DEPENDS ON ⬇️
       ▼
┌──────────────────┐
│ ProductionAgent  │  Reads manifest, creates chapters/
└──────┬───────────┘
       │ ⚠️ DEPENDS ON ⬇️
       ▼
┌──────────────────┐
│ CompilerAgent    │  Reads chapters/, compiles book.pdf
└──────────────────┘

✅ CAN parallelize INSIDE ProductionAgent (per-video)
❌ CANNOT parallelize the root sequence
```

## Per-Video Pipeline (MUST BE SEQUENTIAL)

```
┌────────────┐
│ MediaAgent │  Downloads video, creates transcript
└─────┬──────┘
      │ ⚠️ transcript needed ⬇️
      ▼
┌──────────────┐
│ AnalystAgent │  Reads transcript → analysis.json
└──────┬───────┘
       │ ⚠️ analysis needed ⬇️
       ▼
┌──────────────┐
│ AssetsAgent  │  Reads analysis → creates charts/tables
└──────┬───────┘
       │ ⚠️ assets needed ⬇️
       ▼
┌──────────────┐
│ WriterAgent  │  Reads analysis + assets → chapter.tex
└──────┬───────┘
       │ ⚠️ chapter needed ⬇️
       ▼
┌──────────────┐
│ QA Loop      │  Validates/refines chapter.tex
└──────────────┘

✅ CAN parallelize frame extraction inside MediaAgent
✅ CAN parallelize asset rendering inside AssetsAgent
❌ CANNOT parallelize the per-video sequence
```

## Parallel Video Processing Pattern ✅ RECOMMENDED

```python
# SAFE: Process multiple videos concurrently

┌─────────────────────────────────────────────┐
│         ProductionAgent                     │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │   Semaphore(2)  ← Rate Limit        │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌───────────┐  ┌───────────┐             │
│  │  Video 1  │  │  Video 2  │  ← Running  │
│  │  Pipeline │  │  Pipeline │             │
│  └───────────┘  └───────────┘             │
│                                             │
│  ┌───────────┐                             │
│  │  Video 3  │  ← Waiting for slot         │
│  │  Queued   │                             │
│  └───────────┘                             │
│                                             │
│  manifest_lock ← Prevents race conditions  │
└─────────────────────────────────────────────┘

Speedup: 2x with 2 concurrent, 3x with 3 concurrent
Risk: Medium (needs locking + context isolation)
```

## Race Condition Example ❌ UNSAFE

```python
# WITHOUT LOCKING (BROKEN):

Thread 1: manifest = load()          # Reads: video_A status="pending"
Thread 2: manifest = load()          # Reads: video_A status="pending"
Thread 1: video_A.status = "media"
Thread 2: video_A.status = "failed"
Thread 1: save(manifest)             # Writes: video_A="media"
Thread 2: save(manifest)             # Writes: video_A="failed" ← OVERWRITES!

Result: Lost update (video_A status is wrong)
```

```python
# WITH LOCKING (SAFE):

Thread 1: with lock:
              manifest = load()      # Reads: video_A status="pending"
              video_A.status = "media"
              save(manifest)         # Writes: video_A="media"

Thread 2: with lock:                 # ⏸️ BLOCKS until Thread 1 done
              manifest = load()      # Reads: video_A status="media"
              video_A.status = "failed"
              save(manifest)         # Writes: video_A="failed"

Result: ✅ Correct - updates are serialized
```

## Implementation Priority

### Phase 1: Essential ⭐⭐⭐
```
1. Add manifest locking (asyncio.Lock)       [2 hours]
2. Parallel video processing (2 concurrent)  [1 day]
3. Test with small channel (2-3 videos)      [1 day]
```

### Phase 2: Optimization ⭐⭐
```
4. Parallel frame extraction                 [4 hours]
5. Increase to 3 concurrent videos           [2 hours]
6. Monitor memory/rate limits                [ongoing]
```

### Phase 3: Polish ⭐
```
7. Parallel asset rendering                  [4 hours]
8. Advanced metrics/monitoring               [1 day]
```

## Configuration Options

```python
# config.py
class Settings(BaseSettings):
    # Parallelization controls
    max_concurrent_videos: int = 2      # Videos processed simultaneously
    max_concurrent_frames: int = 4      # Frame extraction workers
    max_concurrent_assets: int = 2      # Asset rendering workers
    
    # Safety limits
    enable_parallel_videos: bool = True
    enable_parallel_frames: bool = True
    enable_parallel_assets: bool = False  # Off by default (low value)
```

## Monitoring Checklist

When running parallel:
- [ ] Watch memory usage (3 videos ≈ 3x memory)
- [ ] Monitor LLM API rate limits
- [ ] Check disk I/O (frame writes)
- [ ] Log manifest update conflicts
- [ ] Track per-video timing
- [ ] Verify no status corruption

## When Things Go Wrong

### Symptom: Manifest corruption (wrong statuses)
**Cause:** No locking on manifest updates  
**Fix:** Add `asyncio.Lock()` around `load_manifest()` + `save_manifest()`

### Symptom: LLM rate limit errors
**Cause:** Too many concurrent videos  
**Fix:** Reduce `max_concurrent_videos` from 3 → 2

### Symptom: Out of memory
**Cause:** Too many videos processing at once  
**Fix:** Reduce `max_concurrent_videos` or increase system RAM

### Symptom: Videos fail randomly
**Cause:** Context isolation broken  
**Fix:** Create separate context per video: `ctx.create_child_context()`

### Symptom: Disk full errors
**Cause:** Parallel frame extraction fills disk  
**Fix:** Clean up `frames_raw/` after deduplication

## Testing Strategy

```bash
# 1. Test with locking but sequential (verify no regression)
BOOKFORGE_MAX_CONCURRENT_VIDEOS=1 python -m bookforge.main <url>

# 2. Test with 2 concurrent (verify speedup)
BOOKFORGE_MAX_CONCURRENT_VIDEOS=2 python -m bookforge.main <url>

# 3. Test with 3 concurrent (verify no issues)
BOOKFORGE_MAX_CONCURRENT_VIDEOS=3 python -m bookforge.main <url>

# 4. Test resume after failure (verify checkpoint works)
# Kill process mid-run, restart, verify it resumes
```

## Performance Expectations

```
Channel Size     Sequential    Parallel (2)    Parallel (3)
─────────────────────────────────────────────────────────────
1 video          5-8 min       5-8 min         5-8 min
5 videos         25-40 min     13-20 min       10-15 min
10 videos        50-80 min     25-40 min       17-27 min
20 videos        100-160 min   50-80 min       35-55 min

Note: Assumes no rate limiting. Actual times may vary.
```

## Key Takeaways

✅ **DO:**
- Parallelize video processing loop (2-3 concurrent)
- Add locking for shared state (manifest)
- Parallelize frame extraction (good for long videos)
- Start conservative (2 concurrent), then scale

❌ **DON'T:**
- Parallelize root pipeline (Intake→Production→Compile)
- Parallelize chapter pipeline (Media→Analyst→Writer)
- Skip locking on manifest updates
- Exceed LLM API rate limits

🎯 **Best ROI:**
Parallel video processing (2 concurrent) = **2x speedup** with **low risk**

---

**Ready to implement?** See `PARALLELIZATION-ANALYSIS.md` for detailed code examples.
