"""
Quantum Tree distillation pipeline runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase2_qaoa.qaoa_runner import OUT
from phase3_quantum_tree.classical_layer import run_classical_layer
from phase3_quantum_tree.distillation import build_distilled_dataset
from phase3_quantum_tree.quantum_layer import QuantumDistillationLayer
from phase3_quantum_tree.student_model import AutonomousStudentModel


def run_quantum_tree_pipeline(seed: int = 42, shots: int = 256) -> Dict[str, Any]:
    classical = run_classical_layer(seed=seed)
    quantum_layer = QuantumDistillationLayer(shots=shots, seed=seed)
    quantum = quantum_layer.refine(classical["hidden"], classical["teacher_probs"])
    distilled_rows = build_distilled_dataset(
        features=classical["features"],
        states=classical["states"],
        labels=classical["labels"],
        teacher_probs=classical["teacher_probs"],
        quantum_scores=quantum["quantum_scores"],
    )

    student = AutonomousStudentModel(seed=seed)
    targets = np.array([row["distilled_target"] for row in distilled_rows], dtype=float)
    student_metrics = student.fit(classical["features"], targets)
    student_preds = student.predict(classical["features"]).reshape(-1)

    ranked = sorted(distilled_rows, key=lambda row: row["distilled_target"], reverse=True)[:10]
    summary = {
        "teacher_accuracy": classical["teacher_metrics"]["accuracy"],
        "teacher_loss": classical["teacher_metrics"]["loss"],
        "quantum_backend": str(quantum["backend"][0]),
        "mean_quantum_score": round(float(np.mean(quantum["quantum_scores"])), 6),
        "mean_teacher_prob": round(float(np.mean(classical["teacher_probs"])), 6),
        "mean_student_score": round(float(np.mean(student_preds)), 6),
        "student_mse": student_metrics["mse"],
    }
    results = {
        "architecture": [
            "Layer 1: classical teacher simulation with backpropagation",
            "Layer 2: quantum refinement layer using IBM Qiskit-compatible sampling",
            "Layer 3: distilled dataset used to train an autonomous student model",
        ],
        "summary": summary,
        "top_distilled_states": ranked,
    }

    (OUT / "quantum_tree_results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the QAA Quantum Tree distillation pipeline")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shots", type=int, default=256)
    args = parser.parse_args()
    results = run_quantum_tree_pipeline(seed=args.seed, shots=args.shots)
    print("Quantum Tree distillation complete")
    print(f"Teacher accuracy : {results['summary']['teacher_accuracy']}")
    print(f"Quantum backend  : {results['summary']['quantum_backend']}")
    print(f"Student MSE      : {results['summary']['student_mse']}")
    print(f"Results written  : {OUT / 'quantum_tree_results.json'}")


if __name__ == "__main__":
    main()
