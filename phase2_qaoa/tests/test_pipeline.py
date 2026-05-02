import json

from phase2_qaoa.comparator import compare_results
from phase2_qaoa.monte_carlo import run_monte_carlo
from phase2_qaoa.qaoa_runner import OUT, QAOAExplorer, evaluate_state
from phase2_qaoa.visualize import render_dashboard


def test_evaluate_state_flags_conflict() -> None:
    result = evaluate_state(
        {
            "int_heading": 90.0,
            "int_altitude": 31000.0,
            "int_speed": 6.0,
            "int_x_offset": 0.0,
        }
    )
    assert result["failure"] is True


def test_full_pipeline_outputs_files() -> None:
    qaoa = QAOAExplorer(reps=1, shots=64, seed=7).run(k_iterations=10)
    mc = run_monte_carlo(k_iterations=10, seed=7)
    comparison = compare_results()
    dashboard = render_dashboard()

    assert qaoa["total_unique_failures"] >= 1
    assert mc["k_iterations"] == 10
    assert comparison["summary"]["qaoa_unique_failures"] >= comparison["summary"]["mc_unique_failures"]
    assert dashboard.exists()
    assert "Panel 1 - Cumulative failures" in dashboard.read_text(encoding="utf-8")
    assert json.loads((OUT / "comparison.json").read_text(encoding="utf-8"))["winner"] == comparison["winner"]
