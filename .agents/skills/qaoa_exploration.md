# qaoa_exploration

Use this repository skill when working on the Phase 2 QAA exploration loop.

## Intent
- Keep the work centered on the paper question: can QAOA surface unsafe traffic separation behaviors faster than Monte Carlo?
- Prefer Qiskit 1.x primitives when available.
- Preserve a laptop-scale 2-aircraft, simulator-only workflow.

## Execution order
1. Read `AGENTS.md`.
2. Read `PLANS.md`.
3. Complete `qubo_encoder.py`, `qaoa_runner.py`, `monte_carlo.py`, `comparator.py`, then `visualize.py`.
4. Run tests and dry-run validation before finalizing.

## Output rules
- All generated artifacts must go to `outputs/`.
- `outputs/dashboard.html` must remain self-contained with no external CDN usage.
- Report whether Qiskit was available locally or whether the deterministic fallback sampler was used.
