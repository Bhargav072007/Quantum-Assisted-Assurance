# PLANS.md - MeghyanAI Portal Rebuild Execution Plan
# Codex works through these steps in order.
# Update STATUS after each step. Do not skip steps.
# Run tests after every step before proceeding.

---

## Step 0 - Environment check
STATUS: [x] completed

```bash
cd Quantum-Assisted-Assurance
python -c "from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline; print('OK')"
python -c "from phase2_qaoa.qaoa_runner import QAOAExplorer; print('OK')"
pytest meghyan_portal/tests/test_portal.py -v
```

Success criteria:
- [ ] All imports resolve
- [ ] Existing tests pass
- [ ] Portal runs on http://127.0.0.1:5055

---

## Step 1 - Add fast=True preset to pipeline.py
STATUS: [x] completed

File: `phase3_quantum_tree/pipeline.py`

Add `fast` parameter. When `fast=True`:
- `k_iterations = 5` (not 50)
- `n_shots = 256` (not 1024)
- Skip writing to disk (`output_path=None`)
- Return dict with: `failures_found`, `teacher_accuracy`, `quantum_backend`, `student_mse`, `top_failures`, `failure_rate`

Success criteria:
- [ ] `run_quantum_tree_pipeline(fast=True)` completes in under 60 seconds
- [ ] Returns a dict (not `None`)
- [ ] Existing slow-path behavior unchanged

---

## Step 2 - Add /api/demo/run endpoint to app.py
STATUS: [x] completed

File: `meghyan_portal/app.py`

- `POST /api/demo/run` - no auth required
- Accept JSON: `{scenario_type: "collision"|"separation"|"obstacle"}`
- Rate limit: 3 per IP per hour (use simple dict in `portal_state.py`)
- Call `run_quantum_tree_pipeline(fast=True)`
- Compute `risk_score = min(100, int(failure_rate*100 + (1-teacher_acc)*20 + 30))`
- Return JSON: `{risk_score, failures_found, teacher_accuracy, quantum_backend, student_mse, top_failures, scenario_type, powered_by}`

Success criteria:
- [ ] `curl -X POST http://127.0.0.1:5055/api/demo/run -H "Content-Type: application/json" -d '{"scenario_type":"collision"}'` returns valid JSON
- [ ] `risk_score` is between 0 and 100
- [ ] 4th request from same IP returns 429
- [ ] No auth cookie required

---

## Step 3 - Rebuild site.css with new design system
STATUS: [x] completed

File: `meghyan_portal/static/css/site.css`

Replace existing CSS entirely. Implement:
- CSS variables: `--bg=#0A0A0A`, `--surface=#111111`, `--border=#1E1E1E`, `--accent=#3B82F6`, `--cyan=#06B6D4`, `--text=#F5F5F5`, `--muted=#9CA3AF`
- Base: body bg, font-family, color
- Components: `.nav`, `.hero`, `.card`, `.btn-primary`, `.btn-secondary`, `.badge`, `.gauge`, `.progress-bar`, `.demo-panel`
- Risk score gauge: SVG-based circle, animated fill
- Scroll reveal: `.reveal` class + `IntersectionObserver` in `site.js`
- Pricing cards: `.pricing-card`, `.pricing-card.featured` (border: `1px solid #3B82F6`)
- Failure severity badges: `.badge-critical` (red), `.badge-high` (amber), `.badge-medium` (blue), `.badge-low` (gray)
- Package tier badges: `.tier-redteam`, `.tier-api`, `.tier-cert`

Success criteria:
- [ ] Page renders correctly in Chrome dark mode
- [ ] No white flash on load
- [ ] All components visible without JS

---

## Step 4 - Rebuild landing.html
STATUS: [x] completed

File: `meghyan_portal/templates/landing.html`

Sections (in order):

### 4a. Nav
- MeghyanAI logo (`static/img/logo.png`)
- Links: How it works | Packages | Pricing
- Buttons: "Sign In" (outline) | "Try Free" (solid blue)

### 4b. Hero
- Badge: "Quantum-powered AI red teaming"
- H1: "We break your AI before your customers do."
- Sub: "MeghyanAI runs a Quantum Tree red team on your autonomous AI - finding the rare failures classical simulation misses."
- Two CTAs: "Run a Free Red Team" (scrolls to demo) | "See Packages" (scrolls to pricing)
- Subtle animated background: CSS-only contour lines (SVG pattern, no JS)

### 4c. Live demo panel
- Headline: "See it in action - no signup required"
- Sub: "Pick a scenario. We run the real Quantum Tree pipeline. Results in 60 seconds."
- Scenario picker: 3 buttons (Collision Avoidance | Traffic Separation | Obstacle Detection)
- "Run Red Team" button -> `POST /api/demo/run`
- Progress bar: 3 stages (Teacher analyzing... -> Quantum refining... -> Student scoring...)
  - Stage 1: 0-40% over 2s
  - Stage 2: 40-80% over 3s
  - Stage 3: 80-100% over 1s
  - All client-side - do not wait for actual API response to animate
- Results panel (hidden until response):
  - Risk Score gauge (SVG circle, animated, color: green<40, amber 40-70, red>70)
  - "X failures discovered" with severity breakdown
  - Top 3 failure cards (type + severity badge + one-line description)
  - Quantum metadata: "Powered by IBM Qiskit · Teacher accuracy: 0.93 · Backend: qiskit-statevector"
  - CTA: "Get the full report ->" -> leads to `/login`

### 4d. How it works
- 3 steps using real pipeline stages

### 4e. Packages (preview)
- 3 cards side by side
- Red Team Scan: `$2,500/run`
- Scenario API: `$500/month`
- Certification Pack: `$10,000/audit`

### 4f. Trust bar
- "Powered by" section: IBM Qiskit | Penn State ICDS | Quantum Tree distillation

### 4g. Footer
- MeghyanAI logo + tagline
- Links: Pricing | Login | GitHub

Success criteria:
- [ ] Page loads without login
- [ ] Demo panel works end-to-end: pick scenario -> click run -> see results
- [ ] Risk score gauge animates correctly
- [ ] All sections visible on 1280px desktop

---

## Step 5 - Add /pricing route and pricing.html
STATUS: [x] completed

File: `meghyan_portal/templates/pricing.html` (new)  
Route: `GET /pricing` in `app.py`

Sections:
- Headline: "Straightforward pricing. Real quantum results."
- Toggle: Per-run vs Monthly (JS toggle, no page reload)
- 3 pricing cards with detailed package info
- FAQ section

Success criteria:
- [ ] /pricing loads without login
- [ ] Toggle switches pricing display between per-run and monthly
- [ ] All 3 cards render with correct info
- [ ] FAQ accordion works

---

## Step 6 - Rebuild studio.html (Quantum Tree Studio)
STATUS: [~] in progress

File: `meghyan_portal/templates/studio.html`

Pull real data from `outputs/quantum_tree_results.json`

Success criteria:
- [ ] Real values from `quantum_tree_results.json` displayed (not hardcoded)
- [ ] "Run new analysis" calls `/api/run/quantum-tree` and updates the page
- [ ] Failure table populated
- [ ] Export button downloads valid JSON

---

## Step 7 - Rebuild runs.html
STATUS: [ ] not started

Show active and completed runs.
Pull data from `portal_state.py` run history.

---

## Step 8 - Rebuild reports.html
STATUS: [ ] not started

Show completed verification reports and package/report metadata.

---

## Step 9 - Final polish + tests
STATUS: [ ] not started

- Add scroll reveal animations to landing sections
- Add loading skeletons for async content
- Add error state for demo panel
- Add rate limit counter to demo panel
- Run full tests

---

## Final delivery checklist
- [ ] Landing page live demo works with real Quantum Tree pipeline
- [ ] Three packages showcased on /pricing with accurate descriptions
- [ ] Studio shows real `quantum_tree_results.json` data
- [ ] All routes accessible (public: /, /pricing | auth: /app/*)
- [ ] Design matches: dark, minimal, professional
- [ ] No hardcoded fake results - everything wired to real pipeline
- [ ] All tests passing
- [ ] README.md updated with new run instructions
