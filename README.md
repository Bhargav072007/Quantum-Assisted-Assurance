# Quantum-Assisted Assurance

Quantum-Assisted Assurance (QAA) is a research prototype for exploring unsafe behavior discovery in autonomous aviation safety verification. This repository currently contains:

- `Phase 2`: direct QAOA vs Monte Carlo comparison over a discretized 3D two-aircraft separation scenario
- `Phase 3`: a hybrid `Quantum Tree` distillation pipeline with a classical teacher, quantum refinement layer, and autonomous student model

## Research status

The current direct-search benchmark does **not** yet show quantum advantage.

Latest validated finding from the real Qiskit-backed run:

- QAOA unique failures: `1`
- Monte Carlo unique failures: `5`
- Current winner in `outputs/comparison.json`: `MonteCarlo`

That means the repo is best understood today as:

- a working benchmark scaffold for QAOA vs Monte Carlo
- a working hybrid architecture prototype for future improvement
- not yet evidence that direct QAOA outperforms classical random search

## Repository layout

```text
qaa_codex/
├── AGENTS.md
├── PLANS.md
├── requirements.txt
├── outputs/
│   ├── qaoa_results.json
│   ├── mc_results.json
│   ├── comparison.json
│   ├── quantum_tree_results.json
│   └── dashboard.html
├── phase2_qaoa/
│   ├── qubo_encoder.py
│   ├── qaoa_runner.py
│   ├── monte_carlo.py
│   ├── comparator.py
│   ├── visualize.py
│   └── tests/
└── phase3_quantum_tree/
    ├── classical_layer.py
    ├── quantum_layer.py
    ├── distillation.py
    ├── student_model.py
    ├── pipeline.py
    └── README.md
```

## Environment setup

This repo was developed locally with a virtual environment at `.venv`.

PowerShell:

```powershell
cd "C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex"
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, you can always call the interpreter directly:

```powershell
& ".\.venv\Scripts\python.exe" --version
```

## Install dependencies

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Phase 2: QAOA vs Monte Carlo

### Dry run

```powershell
& ".\.venv\Scripts\python.exe" phase2_qaoa\qaoa_runner.py --dry-run
```

### Run the full benchmark

```powershell
& ".\.venv\Scripts\python.exe" phase2_qaoa\qaoa_runner.py --reps 2 --shots 1024 --k 50
& ".\.venv\Scripts\python.exe" phase2_qaoa\monte_carlo.py --k 50
& ".\.venv\Scripts\python.exe" phase2_qaoa\comparator.py
& ".\.venv\Scripts\python.exe" phase2_qaoa\visualize.py
```

### Outputs

- `outputs/qaoa_results.json`
- `outputs/mc_results.json`
- `outputs/comparison.json`
- `outputs/dashboard.html`

## Phase 3: Quantum Tree distillation

Quantum Tree is a three-layer hybrid pipeline:

1. Classical teacher simulation with backpropagation
2. Quantum refinement layer using Qiskit-compatible sampling
3. Distilled student model trained on teacher + quantum outputs

### Run Quantum Tree

```powershell
& ".\.venv\Scripts\python.exe" phase3_quantum_tree\pipeline.py --shots 64
```

### Output

- `outputs/quantum_tree_results.json`

Current example metrics:

- teacher accuracy around `0.93`
- quantum backend `qiskit-statevector`
- low student MSE on distilled targets

This is promising as a hybrid training architecture, but it is not yet a direct cumulative-failure benchmark like Monte Carlo vs QAOA.

## MeghyanAI Portal

This repo now also includes a minimal product shell for `MeghyanAI` that wraps the live assurance implementation with:

- a YC-style landing page
- enterprise login
- admin vs customer access rules
- a `Quantum Tree Studio` page
- a chat-style `Analyst` workspace with token metering
- run history, reports, and admin views
- live triggers for the Qiskit-backed Quantum Tree and benchmark workflows

Run it locally:

```powershell
& ".\.venv\Scripts\python.exe" -m meghyan_portal.app
```

Then open:

- `http://127.0.0.1:5055`

Demo credentials:

- admin: `admin@meghyan.ai` / `admin-demo`
- customer: `pilot@aerosafe.ai` / `pilot-demo`

### Optional stronger LLM backend

By default, the Analyst workspace uses the local `meghyan-analyst-local` fallback.

To connect a stronger OpenAI-compatible provider, set these environment variables before starting the portal:

```powershell
$env:MEGHYAN_LLM_MODE="openai_compatible"
$env:MEGHYAN_LLM_ENDPOINT="https://your-provider.example/v1"
$env:MEGHYAN_LLM_API_KEY="your-api-key"
$env:MEGHYAN_LLM_MODEL="your-chat-model"
& ".\.venv\Scripts\python.exe" -m meghyan_portal.app
```

Notes:

- `MEGHYAN_LLM_ENDPOINT` should point to an OpenAI-compatible `/v1` base URL
- the portal sends chat-style messages to `/chat/completions`
- if provider mode is selected but the endpoint or key is missing, the app will show that configuration is incomplete

## Dashboard

Generate the dashboard with:

```powershell
& ".\.venv\Scripts\python.exe" phase2_qaoa\visualize.py
```

Then open:

- `outputs/dashboard.html`

The dashboard currently includes:

- Monte Carlo vs QAOA cumulative failure chart
- failure type breakdown
- summary statistics
- QAOA circuit summary and diagram
- top QAOA failure states
- Quantum Tree architecture summary
- Quantum Tree teacher / quantum / student metrics
- Quantum Tree distilled-state table

## Tests

Run all current tests:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest phase2_qaoa\tests\
```

## Current interpretation

The repo currently supports two research directions:

### Direction 1: direct quantum search

This is the current `Phase 2` benchmark. Right now, Monte Carlo is stronger than direct QAOA on the implemented task.

### Direction 2: hybrid quantum-classical distillation

This is the new `Quantum Tree` approach. It is likely the stronger future direction because it uses:

- a classical teacher to shape the search space
- a quantum layer to refine or reweight candidate structure
- a student model to absorb the distilled signal

## Recommended next steps

- Improve the QUBO/Hamiltonian so it aligns better with true unsafe-state discovery
- Expand the benchmark across multiple seeds and budgets
- Evaluate the Quantum Tree student on the same external benchmark as Monte Carlo and QAOA
- Add a true third comparison curve for the student once it can be evaluated as a search policy
- Move from hand-shaped features toward richer learned latent representations

## Notes

- `AGENTS.md` contains repository-specific guidance for coding agents
- `PLANS.md` records the intended execution flow
- Some temporary pytest cache warnings may appear in OneDrive-backed environments; current passing tests are still valid
