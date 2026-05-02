from phase3_quantum_tree.classical_layer import run_classical_layer
from phase3_quantum_tree.pipeline import run_quantum_tree_pipeline


def test_classical_layer_learns_signal() -> None:
    result = run_classical_layer(seed=11)
    assert result["teacher_metrics"]["accuracy"] >= 0.7
    assert result["hidden"].shape[0] == len(result["states"])


def test_quantum_tree_pipeline_writes_summary() -> None:
    result = run_quantum_tree_pipeline(seed=11, shots=64)
    assert len(result["architecture"]) == 3
    assert result["summary"]["student_mse"] >= 0.0
    assert len(result["top_distilled_states"]) >= 1
