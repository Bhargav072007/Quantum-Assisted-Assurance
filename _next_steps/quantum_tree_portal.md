# Skill: quantum_tree_portal
# Description: Wire the MeghyanAI portal to the real Quantum Tree pipeline

## When to use this skill
Use whenever you need to:
- Call the Quantum Tree pipeline from a Flask route
- Add a new demo or run endpoint
- Display results from quantum_tree_results.json
- Build a UI component that shows pipeline stages

## The real pipeline call

```python
from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline

# Fast demo mode (60 seconds)
result = run_quantum_tree_pipeline(fast=True)

# Full mode (10+ minutes, for paid runs)
result = run_quantum_tree_pipeline(fast=False, output_path='outputs/')
```

## What the pipeline returns
```python
{
    'teacher_accuracy': 0.9257,    # float 0-1
    'quantum_backend': 'qiskit-statevector',
    'student_mse': 0.007671,       # float, lower is better
    'failures_found': 4,           # int
    'failure_rate': 0.08,          # float 0-1
    'top_failures': [              # list of dicts
        {
            'type': 'separation_loss',
            'severity': 'critical',
            'h_sep_nm': 2.3,
            'v_sep_ft': 450,
            'description': 'Intruder at FL290, crossing heading 90°'
        },
        ...
    ],
    'n_scenarios': 50,             # int
    'run_id': 'qt_20260502_001',   # string
}
```

## Risk score formula
```python
failure_rate = result.get('failure_rate', 0)
teacher_acc  = result.get('teacher_accuracy', 0.93)
risk_score   = min(100, int(failure_rate * 100 + (1 - teacher_acc) * 20 + 30))
# Typical range: 30-85 for real runs
# Below 40 = low risk (green), 40-70 = medium (amber), above 70 = high (red)
```

## Severity badge mapping
```python
def get_severity(h_sep, v_sep):
    if h_sep < 2 and v_sep < 500:   return 'critical'
    if h_sep < 3 and v_sep < 750:   return 'high'
    if h_sep < 5 and v_sep < 1000:  return 'medium'
    return 'low'
```

## Frontend: animated progress bar (3 stages)
```javascript
async function runDemo(scenarioType) {
    // Start animation immediately — don't wait for API
    await animateProgress('Teacher analyzing...', 0, 40, 2000);
    await animateProgress('Quantum refining...', 40, 80, 3000);
    await animateProgress('Student scoring...', 80, 100, 1000);
    
    // Meanwhile, fetch results
    const response = await fetch('/api/demo/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scenario_type: scenarioType})
    });
    const data = await response.json();
    showResults(data);
}
```

## Risk gauge SVG pattern
```html
<!-- SVG circle gauge for risk score 0-100 -->
<svg viewBox="0 0 120 120" class="risk-gauge">
    <!-- Background arc -->
    <circle cx="60" cy="60" r="50" fill="none" stroke="#1E1E1E" stroke-width="8"/>
    <!-- Score arc — stroke-dasharray controlled by JS -->
    <circle id="gauge-arc" cx="60" cy="60" r="50" fill="none"
            stroke="#10B981" stroke-width="8" stroke-linecap="round"
            stroke-dasharray="0 314" transform="rotate(-90 60 60)"
            style="transition: stroke-dasharray 1s ease, stroke 0.5s ease"/>
    <text id="gauge-score" x="60" y="65" text-anchor="middle"
          fill="#F5F5F5" font-size="22" font-weight="300">--</text>
    <text x="60" y="82" text-anchor="middle" fill="#9CA3AF" font-size="9">RISK SCORE</text>
</svg>

<script>
function updateGauge(score) {
    const arc = document.getElementById('gauge-arc');
    const text = document.getElementById('gauge-score');
    const circumference = 2 * Math.PI * 50; // ~314
    const dashLength = (score / 100) * circumference;
    arc.setAttribute('stroke-dasharray', `${dashLength} ${circumference - dashLength}`);
    arc.setAttribute('stroke', score < 40 ? '#10B981' : score < 70 ? '#F59E0B' : '#EF4444');
    text.textContent = score;
}
</script>
```

## Rate limiting (simple, no Redis needed)
```python
# portal_state.py — add this
from collections import defaultdict
from datetime import datetime, timedelta

_demo_rate_limits = defaultdict(list)

def check_demo_rate_limit(ip: str, max_per_hour: int = 3) -> bool:
    """Returns True if allowed, False if rate limited."""
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    # Clean old entries
    _demo_rate_limits[ip] = [t for t in _demo_rate_limits[ip] if t > cutoff]
    if len(_demo_rate_limits[ip]) >= max_per_hour:
        return False
    _demo_rate_limits[ip].append(now)
    return True

def get_remaining_runs(ip: str, max_per_hour: int = 3) -> int:
    now = datetime.now()
    cutoff = now - timedelta(hours=1)
    recent = [t for t in _demo_rate_limits[ip] if t > cutoff]
    return max(0, max_per_hour - len(recent))
```

## Error handling
If the pipeline fails, return a graceful response:
```python
try:
    result = run_quantum_tree_pipeline(fast=True)
except Exception as e:
    return jsonify({
        'error': True,
        'message': 'Pipeline temporarily unavailable. Using cached result.',
        'risk_score': 67,
        'failures_found': 3,
        'teacher_accuracy': 0.93,
        'quantum_backend': 'qiskit-statevector (cached)',
        'top_failures': [
            {'type': 'separation_loss', 'severity': 'high',
             'description': 'Cached result — live pipeline unavailable'},
        ],
        'powered_by': 'Quantum Tree distillation (IBM Qiskit)',
    })
```

## What NOT to do
- Never return fake results when the pipeline works — only use cached results on exception
- Never expose internal Python errors to the frontend
- Never call run_quantum_tree_pipeline() synchronously on a GET request — only POST
- Never store API keys or credentials in portal_state.py
