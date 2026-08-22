# GitOps ELI5 — Interactive Learning Hub

A single-file, offline-first HTML artifact that teaches GitOps the ELI5 way,
built from the notes of a video by Vishaka (Senior Solutions Architect) in the
`Yash-Kavaiya/Vishakha-Sadhwani` repository.

## What's inside

| Section | Content |
|---|---|
| 1 · The Big Idea | Git as single source of truth; what lives in Git; why it got popular |
| 2 · Push vs Pull | Traditional CI/CD vs GitOps flows, comparison table, benefits checklist |
| 3 · Argo CD vs Flux CD | Interactive tabs: Argo workflow, Flux controllers, head-to-head table |
| 4 · Drift Demo | Simulate `kubectl edit`, watch drift appear and self-heal on reconcile |
| 5 · Quiz | The four scenario questions with scoring + localStorage persistence |
| 6 · Recap | One-line summary and next steps |

## How to open

No server needed — data and scripts are fully inlined:

- Double-click `index.html`, or
- `python -m http.server 8940 --bind 127.0.0.1` then open http://127.0.0.1:8940/index.html

Works fully offline; progress is stored locally (`localStorage` key
`gitops-eli5-answers`). Print-friendly CSS included.

## Verification

See `VERIFICATION.md` for executed QA evidence (html-validate pass, 23/23
jsdom interaction assertions, overflow audit).

## Files

- `index.html` — the artifact (self-contained)
- `VERIFICATION.md` — executed QA evidence
- `MANIFEST.json` — file listing with SHA-256 checksums
- `SHA256SUMS.txt` — payload integrity (excludes itself)
