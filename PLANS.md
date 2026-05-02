# PLANS.md - QAA Phase 2 Execution Plan

## Objective
Build and run the QAOA exploration pipeline for QAA Phase 2.
Answer: "Does QAOA find unsafe aviation behaviors faster than Monte Carlo?"

## Plan

### Step 1 - QUBO Encoding [qubo_encoder.py]
STATUS: [x] completed

Encode the 3D aviation traffic separation problem as a QUBO:
- Variables: discretized initial state parameters (positions, headings, speeds)
- Objective: maximize probability of separation loss (H < 5NM AND V < 1000ft)
- Penalty terms: ensure physical feasibility constraints
- Output: SparsePauliOp cost Hamiltonian for Qiskit

Success criteria:
- [x] QUBO encodes at least 8 binary variables
- [x] Hamiltonian passes Hermitian check
- [x] `--dry-run` prints circuit without error

### Step 2 - QAOA Runner [qaoa_runner.py]
STATUS: [x] completed

Run QAOA optimization loop:
- Build qaoa_ansatz with cost Hamiltonian from Step 1
- Optimize with COBYLA (classical outer loop) when available
- Sample bitstrings, decode, evaluate in aviation environment
- Record which samples cause separation loss

Success criteria:
- [x] Circuit runs on Qiskit Aer when available, otherwise local fallback sampler runs
- [x] At least 1 failure state discovered per 10 iterations in local validation
- [x] Results saved to outputs/qaoa_results.json

### Step 3 - Monte Carlo Baseline [monte_carlo.py]
STATUS: [x] completed

Run classical random search over same state space:
- Same budget K as QAOA (number of environment evaluations)
- Uniform random sampling of initial state parameters
- Record failures found per iteration

Success criteria:
- [x] Same environment used as QAOA evaluation
- [x] Same K budget
- [x] Results saved to outputs/mc_results.json

### Step 4 - Comparator [comparator.py]
STATUS: [x] completed

Compute coverage comparison:
- Failures found by QAOA vs MC at each iteration k=1..K
- Unique failure states discovered
- Time-to-first-failure (iterations)

Success criteria:
- [x] Produces comparison.json with per-iteration counts
- [x] Computes statistical summary (mean, std across seeds)

### Step 5 - Dashboard [visualize.py]
STATUS: [x] completed

Generate outputs/dashboard.html with:
- Line chart: cumulative failures found QAOA vs MC
- Bar chart: failure types
- Table: top 10 failure states
- QAOA circuit diagram (text representation)
- Summary stats panel

Success criteria:
- [x] dashboard.html opens as a self-contained file
- [x] All 5 visual elements are rendered into the HTML
- [x] No external CDN dependencies

## Do not proceed to next step until current step's criteria are met.
