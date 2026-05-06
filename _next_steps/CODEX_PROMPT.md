# CODEX PROMPT — MeghyanAI Portal Rebuild
# Paste this entire prompt into Codex to start the task.
# The repo already contains AGENTS.md and PLANS.md with full details.

---

Read AGENTS.md and PLANS.md first. Then execute all 9 steps in PLANS.md in order.

Your task is to rebuild the meghyan_portal/ into a product website for MeghyanAI — 
an AI Red Team service powered by the real Quantum Tree distillation pipeline 
(phase3_quantum_tree/pipeline.py).

Key requirements:
1. The landing page (landing.html) must have a LIVE DEMO that runs the REAL 
   Quantum Tree pipeline — no fakes, no mocks. Visitors pick a scenario, 
   click Run, and see actual quantum pipeline results in 60 seconds.

2. Three packages must be clearly showcased on the landing page AND on a 
   dedicated /pricing page:
   - Red Team Scan: $2,500/run
   - Scenario API: $500/month
   - Certification Evidence Pack: $10,000/audit

3. The design must be dark, minimal, and professional — see design system 
   in AGENTS.md. The headline is: "We break your AI before your customers do."

4. Use the $quantum_tree_portal skill for all pipeline wiring decisions.

5. After every step, run:
   pytest meghyan_portal/tests/test_portal.py -v
   All tests must pass before moving to the next step.

6. Do not break any existing pipeline code in phase2_qaoa/ or 
   phase3_quantum_tree/. Only add new routes and templates to meghyan_portal/.

Work autonomously through all 9 steps. Update STATUS in PLANS.md as you go.
Do not ask for confirmation unless a test fails or you hit an ambiguous 
design decision not covered in AGENTS.md.

When done, run the full smoke test:
- GET / → landing page loads, demo panel visible
- POST /api/demo/run with {"scenario_type":"collision"} → returns valid JSON with risk_score
- GET /pricing → 3 package cards visible
- GET /login → login page
- POST /login with admin credentials → redirects to /app
- GET /app/studio → shows real quantum_tree_results.json data

Report back with:
1. What was built
2. Any tests that failed and how they were fixed  
3. The exact command to run the portal locally
4. Any decisions made where AGENTS.md was ambiguous
