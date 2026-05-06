# AGENTS.md — MeghyanAI Portal Rebuild
# Read this file first. Every decision Codex makes must be grounded here.

## Project identity
- Company: MeghyanAI
- Tagline: "We break your AI before your customers do"
- Product: AI Red Team as a Service — powered by real Quantum Tree distillation
- Repo: github.com/Bhargav072007/Quantum-Assisted-Assurance
- Stack: Python / Flask / Jinja2 / vanilla JS / CSS

## What this task is
Rebuild the meghyan_portal/ into a product that:
1. Has a public landing page with a LIVE DEMO — no login required
2. Shows three sellable pricing packages backed by real Quantum Tree runs
3. Runs the actual quantum pipeline (phase3_quantum_tree/) on demo requests
4. Looks minimal, dark, Apple-quality — not a research dashboard

## Repository layout (DO NOT change these paths)
```
Quantum-Assisted-Assurance/
├── AGENTS.md                        ← this file
├── PLANS.md                         ← execution checklist
├── phase2_qaoa/                     ← QAOA vs MC pipeline (keep intact)
│   ├── qubo_encoder.py
│   ├── qaoa_runner.py
│   ├── monte_carlo.py
│   ├── comparator.py
│   └── visualize.py
├── phase3_quantum_tree/             ← THE REAL ENGINE — wire everything to this
│   ├── classical_layer.py           ← teacher network (accuracy 0.93)
│   ├── quantum_layer.py             ← Qiskit quantum refinement
│   ├── distillation.py              ← blend teacher + quantum
│   ├── student_model.py             ← distilled student
│   └── pipeline.py                  ← orchestrator — call this for demo runs
├── outputs/                         ← JSON results land here
│   ├── quantum_tree_results.json
│   ├── comparison.json
│   └── dashboard.html
└── meghyan_portal/                  ← REBUILD THIS
    ├── app.py                       ← Flask app
    ├── portal_state.py              ← state management
    ├── static/
    │   ├── css/site.css
    │   └── js/site.js
    └── templates/
        ├── base.html
        ├── landing.html             ← PUBLIC — no login
        ├── login.html
        ├── dashboard.html           ← logged in
        ├── studio.html              ← Quantum Tree Studio
        ├── runs.html
        ├── reports.html
        └── admin.html
```

## The three packages to build and showcase

### Package 1 — Red Team Scan  ($2,500/run)
- Single AI policy stress-test
- Runs: phase3_quantum_tree/pipeline.py with scenario_type param
- Output: failure catalog (type, severity, decision trace)
- Turnaround: 60 seconds in demo mode (fast preset), 10 min in full mode
- Target buyer: startup CTO validating before launch

### Package 2 — Scenario Generator API  ($500/month or $0.10/scenario)
- Batch quantum-biased scenario generation
- Calls quantum_layer.py to sample rare-event states
- Output: structured JSON scenarios for AI training pipelines
- Delivered via /api/scenarios endpoint
- Target buyer: ML engineer who needs edge-case training data

### Package 3 — Certification Evidence Pack  ($10,000/audit)
- Full DO-178C evidence package
- Runs full pipeline: teacher + quantum + student + comparator
- Output: PDF report + decision_traces.jsonl + coverage metrics
- Generates outputs/verification_report.json
- Target buyer: aerospace prime, defense contractor

## Live demo spec (most important feature)
Located on landing page — NO LOGIN REQUIRED.

### User flow:
1. Visitor sees hero section with "Try it free" CTA
2. Clicks → demo panel slides open (no page redirect)
3. Picks a scenario from 3 presets:
   - "Collision avoidance" → scenario_type="collision"
   - "Traffic separation" → scenario_type="separation"  
   - "Obstacle detection" → scenario_type="obstacle"
4. Clicks "Run Red Team" button
5. Animated progress bar plays (3 stages: Teacher → Quantum → Student)
6. Results appear:
   - Risk Score gauge (0–100)
   - Failures discovered (count + severity badges)
   - Top 3 failure types as cards
   - "Get full report" CTA → leads to signup

### Backend for demo:
- Route: POST /api/demo/run
- Calls: phase3_quantum_tree/pipeline.py with fast=True preset
- Returns JSON: {risk_score, failures_found, top_failures[], teacher_accuracy, quantum_backend}
- Fast preset: k_iterations=5, n_shots=256 (completes in <60s on laptop)
- No auth required for this endpoint
- Rate limit: 3 runs per IP per hour

## Quantum Tree — how to wire it correctly

### The actual call sequence Codex must implement:
```python
# meghyan_portal/app.py — demo endpoint
from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline

@app.route('/api/demo/run', methods=['POST'])
def demo_run():
    scenario_type = request.json.get('scenario_type', 'collision')
    
    # Map scenario to pipeline params
    scenario_params = {
        'collision':  {'intruder_heading': 90,  'altitude_band': 'FL290'},
        'separation': {'intruder_heading': 105, 'altitude_band': 'FL310'},
        'obstacle':   {'intruder_heading': 75,  'altitude_band': 'FL270'},
    }
    
    result = run_quantum_tree_pipeline(
        scenario_params=scenario_params[scenario_type],
        fast=True,           # k=5, shots=256
        output_path=None     # don't write to disk for demo
    )
    
    # Derive risk score from teacher accuracy + failure rate
    failure_rate = result.get('failure_rate', 0)
    teacher_acc  = result.get('teacher_accuracy', 0.93)
    risk_score   = min(100, int(failure_rate * 100 + (1 - teacher_acc) * 20 + 30))
    
    return jsonify({
        'risk_score':       risk_score,
        'failures_found':   result.get('failures_found', 0),
        'teacher_accuracy': teacher_acc,
        'quantum_backend':  result.get('quantum_backend', 'qiskit-statevector'),
        'student_mse':      result.get('student_mse', 0),
        'top_failures':     result.get('top_failures', []),
        'scenario_type':    scenario_type,
        'powered_by':       'Quantum Tree distillation (IBM Qiskit)',
    })
```

### If pipeline.py needs a fast=True param, add it:
```python
# phase3_quantum_tree/pipeline.py — add fast preset support
def run_quantum_tree_pipeline(scenario_params=None, fast=False, output_path='outputs/'):
    k = 5 if fast else 50
    shots = 256 if fast else 1024
    # ... rest of existing pipeline ...
```

## Design system — enforce these rules strictly

### Visual direction
- Background: #0A0A0A (near black)
- Surface: #111111 (cards, panels)
- Border: #1E1E1E (subtle separator)
- Accent blue: #3B82F6 (CTA buttons, highlights)
- Accent cyan: #06B6D4 (secondary accent, from logo)
- Text primary: #F5F5F5
- Text secondary: #9CA3AF
- Success: #10B981
- Warning: #F59E0B
- Danger: #EF4444

### Typography
- Font: system-ui, -apple-system, sans-serif
- Hero headline: 64px, weight 300 (light)
- Section headline: 40px, weight 400
- Card title: 18px, weight 500
- Body: 15px, weight 400, line-height 1.7
- Label: 11px, weight 500, letter-spacing 0.08em, uppercase

### Component rules
- Cards: background #111111, border 1px solid #1E1E1E, border-radius 12px
- Buttons: primary = solid #3B82F6, secondary = transparent + border #3B82F6
- No gradients on backgrounds
- Thin 1px borders only — no thick outlines
- Generous whitespace — 80px section padding minimum
- Animations: opacity + transform only, 300ms ease

### What it should feel like
Palantir operational clarity + Stripe product polish + MeghyanAI aviation identity.
Dark, serious, credible. Not sci-fi. Not a research tool.

## Auth system — keep existing, extend it
- Admin: admin@meghyan.ai / admin-demo → unlimited runs, all packages
- Customer (Red Team): redteam@client.ai / rt-demo → Package 1 access
- Customer (API): api@client.ai / api-demo → Package 2 access
- Customer (Enterprise): enterprise@client.ai / ent-demo → Package 3 access
- New: unauthenticated visitors → demo only (3 runs/hour rate limit)

## Pages to build/rebuild

### 1. landing.html (PUBLIC — highest priority)
Sections in order:
- Nav: logo + "Sign In" + "Try Free" CTA
- Hero: large headline, sub, animated demo panel
- Live demo panel (the 60-second Quantum Tree runner)
- "How it works" — 3 steps using real pipeline stages
- Packages section — 3 pricing cards (Red Team / API / Certification)
- Trust bar: IBM Qiskit + Penn State ICDS + quantum computing logos
- Footer: minimal

### 2. studio.html (Quantum Tree Studio — logged in)
Show the real 3-layer pipeline as a visual workflow:
- Layer 1 card: Classical Teacher — show accuracy 0.93, training status
- Layer 2 card: Quantum Refinement — show circuit depth 42, backend, qubit count
- Layer 3 card: Distilled Student — show MSE, scenarios tested
- Failure ranking table: pull from outputs/quantum_tree_results.json
- "Run new analysis" button → calls /api/run/quantum-tree

### 3. runs.html (Assurance Runs)
- Active runs with progress bars
- Completed runs with risk scores
- Each run shows: scenario type, package tier, failures found, risk score

### 4. reports.html (Verification Reports)
- Report cards with risk score gauge
- Download buttons (PDF placeholder + JSON real)
- Compliance metadata: DO-178C, run date, model version

### 5. pricing.html (NEW — public page)
Dedicated pricing page with all 3 packages.
Add "Compare" toggle: monthly vs per-run pricing.
Add FAQ section.

## API endpoints to implement
```
POST /api/demo/run          → no auth, rate limited, fast preset
POST /api/run/quantum-tree  → auth required, full pipeline
POST /api/run/benchmark     → auth required, QAOA vs MC
GET  /api/results/latest    → returns quantum_tree_results.json
GET  /api/scenarios         → Package 2: batch scenario generation
GET  /api/report/<run_id>   → Package 3: certification evidence JSON
```

## Testing requirements
After every change, run:
```bash
pytest meghyan_portal/tests/test_portal.py -v
python -c "from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline; print('pipeline OK')"
```
All tests must pass. Never break existing pipeline imports.

## What Codex must NOT do
- Do not mock or fake the Quantum Tree pipeline results — call the real pipeline
- Do not use placeholder lorem ipsum text — use real MeghyanAI copy
- Do not remove the admin/customer auth system
- Do not change phase2_qaoa/ or phase3_quantum_tree/ core logic
- Do not add heavy JS frameworks (React, Vue) — vanilla JS only
- Do not use gradients as backgrounds
- Do not add purple-heavy or neon-glow "AI startup" aesthetics

## Copy to use throughout
Hero headline: "We break your AI before your customers do."
Sub: "MeghyanAI runs a Quantum Tree red team on your autonomous AI — finding the rare failures classical simulation misses."
Package 1 CTA: "Run a Red Team"
Package 2 CTA: "Get API Access"  
Package 3 CTA: "Request Certification Audit"
Demo CTA: "Try it free — no signup required"
Trust line: "Powered by IBM Qiskit · Quantum Tree distillation · Penn State ICDS research"
