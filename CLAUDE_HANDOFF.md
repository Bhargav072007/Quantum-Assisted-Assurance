# MeghyanAI Portal Handoff

## Repo
- Path: `C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex`
- App entrypoint: `meghyan_portal/app.py`
- Portal URL when running locally: `http://127.0.0.1:5055`

## Current product state
- The public marketing site has been redesigned around MeghyanAI branding.
- The landing page hero is simplified and the old right-side hero result card has been removed.
- Transparent white SVG logo assets are now in use:
  - `meghyan_portal/static/img/lockup-white.svg`
  - `meghyan_portal/static/img/mark-white.svg`
- The live demo uses the real Quantum Tree pipeline through `/api/demo/run`.
- The dashboard, studio, reports, and analyst shell are all wired into the real repo outputs.
- Tier-aware product behavior exists for:
  - `redteam`
  - `api`
  - `enterprise`
  - `admin`

## Important files
- Landing page: `meghyan_portal/templates/landing.html`
- Pricing page: `meghyan_portal/templates/pricing.html`
- App shell: `meghyan_portal/templates/app_base.html`
- Dashboard: `meghyan_portal/templates/dashboard.html`
- Analyst: `meghyan_portal/templates/assistant.html`
- Main styles: `meghyan_portal/static/css/site.css`
- Main scripts: `meghyan_portal/static/js/site.js`
- Portal routes and metrics: `meghyan_portal/app.py`
- Portal state: `meghyan_portal/portal_state.py`
- Analyst logic: `meghyan_portal/analysis_engine.py`
- LLM integration: `meghyan_portal/llm_service.py`
- Real pipeline: `phase3_quantum_tree/pipeline.py`

## What is working
- `pytest meghyan_portal/tests/test_portal.py -q` passes.
- The landing page, pricing page, login, dashboard, studio, and analyst routes load.
- The live demo endpoint returns real pipeline-backed JSON.
- The demo is rate-limited to 3 runs per hour per IP.
- The app now sends no-cache HTML headers to reduce stale in-app browser issues.

## Biggest remaining issue
- The Analyst still feels weak because the running server is still in `local` mode.
- Current observed LLM status:
  - `mode: local`
  - `model: meghyan-analyst-local`
- So the Analyst is not yet using a provider-backed model in the live app.

## What was already done for LLM support
- `meghyan_portal/llm_service.py` supports:
  - local fallback mode
  - OpenAI-compatible provider mode
- It now also auto-loads env config from:
  - `.env`
  - `.env.local`
  - `meghyan_portal/.env`

## Exact next step for Analyst
1. Create `.env.local` in the repo root with:

```env
MEGHYAN_LLM_MODE=openai_compatible
MEGHYAN_LLM_ENDPOINT=https://api.openai.com/v1
MEGHYAN_LLM_API_KEY=YOUR_FRESH_API_KEY
MEGHYAN_LLM_MODEL=gpt-5.4-mini
```

2. Restart the portal:

```powershell
cd "C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex"
.\.venv\Scripts\python.exe -m meghyan_portal.app
```

3. Verify in the running app that the Analyst switches away from local mode.

## Design state
- Branding has been updated to the new white transparent logo.
- The landing page is much cleaner than before, but could still be polished further.
- The user specifically wanted:
  - simple
  - minimal
  - Apple / ChatGPT / Claude-like
  - less jargon
- The dashboard and analyst have been simplified, but may still need one more refinement pass.

## Known user preferences
- They dislike:
  - toy-like or “kids diagram” visuals
  - technical jargon in hero copy
  - cluttered dashboard panels
  - repetitive analyst responses
- They want:
  - a professional YC-ready product
  - MeghyanAI branding
  - minimal, dark, premium visual language
  - an Analyst that genuinely feels LLM-backed

## Good local test commands
```powershell
cd "C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex"
.\.venv\Scripts\python.exe -m pytest meghyan_portal/tests/test_portal.py -q
.\.venv\Scripts\python.exe -m meghyan_portal.app
```

## Copy-paste Claude Code prompt
Use this in Claude Code:

```text
You are continuing work on the MeghyanAI portal in:
C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex

Read these first:
- CLAUDE_HANDOFF.md
- meghyan_portal/app.py
- meghyan_portal/llm_service.py
- meghyan_portal/templates/assistant.html
- meghyan_portal/templates/landing.html
- meghyan_portal/static/css/site.css
- meghyan_portal/static/js/site.js

Current state:
- The portal is working and tests pass.
- The branding has been updated to transparent white SVG logos.
- The landing page is simplified and the right-side hero card is removed.
- The live demo is real and pipeline-backed.
- The dashboard and analyst were cleaned up.
- The main remaining problem is that the Analyst still runs in local fallback mode unless provider env vars are configured.

Your top priority:
1. Finish the Analyst so it feels truly production-grade.
2. If `.env.local` exists, ensure the app uses the OpenAI-compatible provider mode correctly.
3. Make the Analyst UI feel more polished and LLM-like.
4. Keep the visual design minimal and premium.

Constraints:
- Do not break the existing pipeline wiring.
- Keep MeghyanAI branding.
- Keep the landing page minimal.
- Run:
  pytest meghyan_portal/tests/test_portal.py -q
  after your changes.
```
