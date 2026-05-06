# Skill: quantum_tree_portal
# Description: Wire the MeghyanAI portal to the real Quantum Tree pipeline

## When to use this skill
Use whenever you need to:
- Call the Quantum Tree pipeline from a Flask route
- Add a new demo or run endpoint
- Display results from `quantum_tree_results.json`
- Build a UI component that shows pipeline stages

## The real pipeline call
```python
from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline

# Fast demo mode (60 seconds)
result = run_quantum_tree_pipeline(fast=True)

# Full mode (10+ minutes, for paid runs)
result = run_quantum_tree_pipeline(fast=False, output_path='outputs/')
```

## Risk score formula
```python
failure_rate = result.get('failure_rate', 0)
teacher_acc  = result.get('teacher_accuracy', 0.93)
risk_score   = min(100, int(failure_rate * 100 + (1 - teacher_acc) * 20 + 30))
```

## Severity badge mapping
```python
def get_severity(h_sep, v_sep):
    if h_sep < 2 and v_sep < 500:
        return 'critical'
    if h_sep < 3 and v_sep < 750:
        return 'high'
    if h_sep < 5 and v_sep < 1000:
        return 'medium'
    return 'low'
```

## Rate limiting
```python
from collections import defaultdict
from datetime import datetime, timedelta

_demo_rate_limits = defaultdict(list)
```

## What NOT to do
- Never return fake results when the pipeline works
- Never expose Python errors to the frontend
- Never call `run_quantum_tree_pipeline()` synchronously on a GET request
- Never store API keys or credentials in `portal_state.py`
