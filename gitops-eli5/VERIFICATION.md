# VERIFICATION — GitOps ELI5 Interactive Hub

Date: 2026-08-22
Artifact: `index.html` (single file, self-contained, offline-capable)
Served URL during QA: http://127.0.0.1:8940/index.html (python http.server, HTTP 200)

## Standards gate

- Command: `npx --yes html-validate index.html`
- Initial run: 9 errors (8 × no-inline-style, 1 × wcag/h32 missing submit button)
- Fixes applied: inline styles moved to CSS classes (`.tight`, `.sub`, `.gap-top`,
  `.hidden-note`, `.bare`, `.visually-hidden`); added `type="submit"`
  "Check answers" button wired via form `submit` handler with
  `preventDefault`.
- Final run: **PASS (0 errors, 0 warnings)**

## Interaction matrix (jsdom probe — 23/23 assertions PASS)

| Interaction class | Test | Result |
|---|---|---|
| Structure | Title + 6 sections + 3 tabs present | PASS |
| Tabs | Default Argo selected; click Flux → "Source Controller" panel; click Head-to-head → table renders | PASS |
| Quiz scoring | All correct answers → "Score: 4 / 4", all feedback `ok` | PASS |
| Quiz scoring | Wrong answer on Q1 → "Score: 3 / 4", feedback `no` | PASS |
| Persistence | Answers saved to localStorage key `gitops-eli5-answers` | PASS |
| Reset | Score/radios/storage cleared ("Score: 0 / 4", storage `{}`) | PASS |
| Drift demo | Heal-before-drift shows noop message | PASS |
| Drift demo | kubectl edit → cluster v2 + OutOfSync badge | PASS |
| Drift demo | Reconcile → v1 restored + Synced badge + "Self-healed" message | PASS |
| Script health | 0 runtime errors during all interactions | PASS |

## Layout / responsive audit

- Viewport meta `width=device-width, initial-scale=1` present.
- Static overflow audit: only fixed widths found are `max-width: 980px`
  (page container — shrinks naturally) and the comparison table's
  `min-width: 560px`, which is intentionally inside a `.table-scroll`
  component-level horizontal scroller (`overflow-x: auto`) so mobile users
  scroll within the table, not the document. No uncontained wide elements.
- Mobile breakpoint at 640px reduces padding/heading size and hides the
  progress widget.

## Accessibility

- Semantic headings h1→h3, landmarks (header/nav/main/footer), tablist/tab/tabpanel roles with `aria-selected`/`aria-controls`.
- All tables use `<th scope>`; hidden caption for comparison table.
- Radio groups in labeled fieldset; visible focus outlines via `:focus-visible`.
- `prefers-reduced-motion` disables transitions/smooth-scroll; print CSS hides chrome.

## Security scan

- No credentials, tokens, or API keys embedded (grep for token/key patterns: none).
- No external network requests — zero third-party assets; works from `file://`.

## Defects found and fixed

1. Inline styles (validator blockers) → moved to classes.
2. Form lacked submit button (wcag/h32) → added "Check answers" submit control.

## Known limitation

Full pixel-level browser screenshot pass was blocked because Chrome's remote-debugging
permission popup was not approved during this session; interaction correctness is
therefore evidenced by the jsdom DOM/script probe above plus a static layout audit,
not screenshots.
