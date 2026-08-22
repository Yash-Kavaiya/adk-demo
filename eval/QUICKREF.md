# BookForge Evaluation Quick Reference

## 🚀 Quick Commands

```bash
# Validate eval sets
python eval/validate_evalset.py eval/*.evalset.json

# Run smoke tests (2 cases, ~5 min)
adk eval bookforge eval/bookforge.evalset.json

# Run full suite (28 cases, ~30-60 min)
adk eval bookforge eval/bookforge-comprehensive.evalset.json

# Run specific category
adk eval bookforge eval/bookforge-comprehensive.evalset.json --filter intake_
adk eval bookforge eval/bookforge-comprehensive.evalset.json --filter e2e_
```

## 📊 Test Categories

| Prefix | Agent/Area | Count | Time |
|--------|-----------|-------|------|
| `intake_` | ChannelIntakeAgent | 3 | ~45s |
| `media_` | MediaAcquisitionAgent | 4 | ~8min |
| `analyst_` | TranscriptAnalystAgent | 3 | ~6min |
| `assets_` | VisualAssetAgent | 3 | ~2min |
| `writer_` | ChapterWriterAgent | 2 | ~8min |
| `critic_` | ChapterCriticAgent | 3 | ~6min |
| `refiner_` | ChapterRefinerAgent | 1 | ~4min |
| `compiler_` | BookCompilerAgent | 2 | ~3min |
| `e2e_` | Full pipeline | 3 | ~45min |
| `orchestration_` | Multi-agent coordination | 2 | ~12min |
| `config_` | Settings & routing | 2 | ~3min |

## 🔧 Prerequisites

### Minimal (smoke tests)
- Network access to YouTube
- `GOOGLE_API_KEY` or Vertex AI credentials

### Full (comprehensive)
- All minimal requirements
- `OPENAI_API_KEY` (for NVIDIA NIM tests)
- `ffmpeg` on PATH
- `pdflatex` on PATH (optional)

## 🛠️ Environment Setup

```bash
# Google AI Studio
export GOOGLE_API_KEY="your-key"

# NVIDIA NIM
export BOOKFORGE_OPENAI_API_KEY="your-nvidia-key"
export BOOKFORGE_OPENAI_API_BASE="https://integrate.api.nvidia.com/v1"

# Vertex AI
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT="your-project"
export GOOGLE_CLOUD_LOCATION="us-central1"

# Optional overrides
export BOOKFORGE_MAX_VIDEOS=2
export BOOKFORGE_COMPILE_LATEX=false
export BOOKFORGE_QA_MAX_ITERATIONS=2
```

## 📁 File Structure

```
eval/
├── bookforge.evalset.json                  # Smoke tests (2 cases)
├── bookforge-comprehensive.evalset.json    # Full suite (28 cases)
├── README.md                               # Detailed guide
├── EVALUATION-SUMMARY.md                   # Coverage analysis
├── QUICKREF.md                             # This file
└── validate_evalset.py                     # JSON validator
```

## ✅ Validation

```bash
# Validate all eval sets
python eval/validate_evalset.py eval/*.evalset.json

# Expected output
[OK] bookforge.evalset.json: Valid
   - eval_set_id: bookforge_smoke
   - eval_cases: 2
   
[OK] bookforge-comprehensive.evalset.json: Valid
   - eval_set_id: bookforge_comprehensive
   - eval_cases: 28
```

## 🐛 Troubleshooting

### YouTube rate limit
```
Error: HTTP 429
```
**Fix:** Wait 1 hour or use different channel

### Missing ffmpeg
```
ffmpeg not found
```
**Fix:** Install from https://ffmpeg.org/

### API quota exceeded
```
429 quota exceeded
```
**Fix:** Wait for quota reset or use different key

### pdflatex unavailable
```
pdflatex not found
```
**Fix:** Install TeX Live or set `BOOKFORGE_COMPILE_LATEX=false`

## 📈 Expected Pass Rates

| Environment | Smoke | Comprehensive |
|-------------|-------|---------------|
| Full (ffmpeg + pdflatex) | 100% | 100% |
| No pdflatex | 100% | ~96% (skip compile tests) |
| No ffmpeg | 50% | ~60% (media tests fail) |
| Network issues | Variable | Variable |

## 🎯 Coverage Summary

- ✅ **9/9 agents** covered
- ✅ **11/11 tools** covered
- ✅ **6 workflows** tested
- ✅ **Error handling** validated
- ✅ **Configuration** scenarios
- ⚠️ **10 gaps** identified (see EVALUATION-SUMMARY.md)

## 📝 Adding New Tests

1. Choose prefix: `{category}_{nn}_{description}`
2. Define minimal `session_input.state`
3. Specify `final_response` substring match
4. Add to `eval_cases` array
5. Run validation: `python eval/validate_evalset.py ...`
6. Update this doc and EVALUATION-SUMMARY.md

## 🔗 Related Docs

- **Full guide:** [eval/README.md](README.md)
- **Coverage:** [eval/EVALUATION-SUMMARY.md](EVALUATION-SUMMARY.md)
- **Main README:** [README.md](../README.md)
- **Architecture:** [solution-architecture.md](../solution-architecture.md)

## 💡 Pro Tips

1. **Start small:** Run smoke tests before comprehensive
2. **Use filters:** Target specific categories during dev
3. **Check logs:** `~/.adk/logs/` has full execution traces
4. **Validate first:** Always validate JSON before running
5. **Mock data:** Pre-populate `state` to test agents in isolation
6. **Parallel runs:** Not yet supported by ADK, runs sequentially
7. **Flaky tests:** Network/YouTube issues can cause intermittent failures
8. **Workspace cleanup:** Remove `data/` between runs for clean slate

## 📞 Support

**Issues:** https://github.com/your-org/bookforge/issues  
**Docs:** eval/README.md  
**Maintainer:** BookForge Team

---

**Version:** 1.0.0  
**Last Updated:** 2026-08-22
