# AGENTS.md — QAA Quantum-Assisted Assurance Project
# This file guides Codex on how to work in this repository.

## Project Overview
This is the QAA (Quantum-Assisted Assurance) research project for autonomous
aviation safety verification. The goal is Phase 2: using QAOA (Quantum
Approximate Optimization Algorithm) via IBM Qiskit to discover rare unsafe
traffic separation behaviors faster than classical Monte Carlo simulation.

## Repository Structure
```
qaa_codex/
├── AGENTS.md                  ← YOU ARE HERE — Codex reads this first
├── PLANS.md                   ← execution plan for multi-step tasks
├── .agents/skills/
│   └── qaoa_exploration.md    ← QAOA skill definition
├── phase2_qaoa/
│   ├── qubo_encoder.py        ← encode 3D airspace as QUBO problem
│   ├── qaoa_runner.py         ← run QAOA on Qiskit Aer simulator
│   ├── monte_carlo.py         ← classical baseline for comparison
│   ├── comparator.py          ← QAOA vs MC coverage comparison
│   └── visualize.py           ← produce visible HTML output dashboard
├── outputs/
│   ├── qaoa_results.json      ← raw QAOA run results
│   ├── comparison.json        ← QAOA vs MC comparison data
│   └── dashboard.html         ← VISIBLE OUTPUT — open this in browser
└── requirements.txt
```

## Model to Use
Use **gpt-5.3-codex** (default) or **gpt-5.4-mini** for lighter subtasks.
Set reasoning effort to **medium** for interactive work, **high** for the
QAOA optimization loop which requires deeper deliberation.

## Core Task for Codex
The primary task is Phase 2 of QAA:

1. Encode the 3D aviation traffic separation decision space as a QUBO
   (Quadratic Unconstrained Binary Optimization) problem
2. Run QAOA via IBM Qiskit Aer simulator to find failure-inducing initial states
3. Compare QAOA coverage vs classical Monte Carlo over K iterations
4. Produce a visible HTML dashboard showing results

## How to Run
```bash
# Install dependencies
pip install -r requirements.txt

# Step 1: Run QAOA exploration
python phase2_qaoa/qaoa_runner.py

# Step 2: Run Monte Carlo baseline
python phase2_qaoa/monte_carlo.py

# Step 3: Compare results
python phase2_qaoa/comparator.py

# Step 4: Generate visible dashboard
python phase2_qaoa/visualize.py

# Open outputs/dashboard.html in your browser
```

## Testing
After ANY code change, run:
```bash
python -m pytest phase2_qaoa/tests/ -v
python phase2_qaoa/qaoa_runner.py --dry-run
```
All tests must pass before submitting. Never skip tests.

## Code Standards
- Python 3.10+ only
- Type hints on all functions
- Docstrings on all classes and public methods
- No hardcoded paths — use pathlib.Path(__file__).parent
- All outputs go to outputs/ directory
- Qiskit version: 1.x (NOT 0.x — do not use qiskit-terra)

## Qiskit-Specific Rules
- Use `qiskit_aer` for simulation (NOT `qiskit.providers.aer`)
- Use `StatevectorSampler` from `qiskit.primitives`
- Use `SparsePauliOp` for Hamiltonian construction
- Use `qaoa_ansatz` from `qiskit.circuit.library`
- COBYLA optimizer from `qiskit_algorithms.optimizers`
- Never import from `qiskit.opflow` — deprecated in Qiskit 1.x

## What Good Output Looks Like
The dashboard.html must show:
1. A line chart: QAOA failures found vs MC failures found over K iterations
2. A bar chart: failure types (separation_loss vs near_miss)
3. A table: top 10 failure-inducing initial states discovered
4. Circuit diagram of the QAOA ansatz used
5. Summary statistics panel

## Autonomy Level
Codex should work autonomously through all 4 steps without asking for
confirmation unless it hits a test failure or ambiguous design decision.
When uncertain about QUBO encoding parameters, use the defaults in qubo_encoder.py.

## Key Research Question (do not lose sight of this)
"Can QAOA-assisted exploration surface unsafe traffic separation behaviors
faster than classical Monte Carlo simulation?"

All code must be oriented toward answering this question with measurable output.
