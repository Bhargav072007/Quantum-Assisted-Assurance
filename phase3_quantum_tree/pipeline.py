"""
Quantum Tree distillation pipeline runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase2_qaoa.qaoa_runner import OUT
from phase2_qaoa.qaoa_runner import evaluate_state
from phase3_quantum_tree.classical_layer import run_classical_layer
from phase3_quantum_tree.distillation import build_distilled_dataset
from phase3_quantum_tree.quantum_layer import QuantumDistillationLayer
from phase3_quantum_tree.student_model import AutonomousStudentModel


def _severity_from_eval(evaluation: Dict[str, Any]) -> str:
    h_sep = float(evaluation["min_h_sep_nm"])
    v_sep = float(evaluation["min_v_sep_ft"])
    if h_sep < 2.0 and v_sep < 500.0:
        return "critical"
    if h_sep < 3.0 and v_sep < 750.0:
        return "high"
    if h_sep < 5.0 and v_sep < 1000.0:
        return "medium"
    return "low"


def _scenario_alignment(state: Dict[str, float], scenario_params: Optional[Dict[str, Any]]) -> float:
    if not scenario_params:
        return 0.0
    score = 0.0
    heading = scenario_params.get("intruder_heading")
    if heading is not None:
        score -= abs(float(state["int_heading"]) - float(heading)) / 180.0
    altitude_band = scenario_params.get("altitude_band")
    if altitude_band:
        try:
            altitude_target = int(str(altitude_band).replace("FL", "")) * 100.0
            score -= abs(float(state["int_altitude"]) - altitude_target) / 10000.0
        except ValueError:
            pass
    return score


def _build_top_failures(
    distilled_rows: List[Dict[str, float]],
    scenario_params: Optional[Dict[str, Any]],
    candidate_budget: int,
) -> tuple[List[Dict[str, Any]], int, float]:
    ranked_rows = sorted(
        distilled_rows,
        key=lambda row: (row["distilled_target"] + _scenario_alignment(row, scenario_params), row["hard_label"]),
        reverse=True,
    )
    candidate_rows = ranked_rows[:candidate_budget]
    top_failures: List[Dict[str, Any]] = []
    failures_found = 0

    for row in candidate_rows:
        state = {
            "int_heading": row["int_heading"],
            "int_altitude": row["int_altitude"],
            "int_speed": row["int_speed"],
            "int_x_offset": row["int_x_offset"],
        }
        evaluation = evaluate_state(state)
        if evaluation["failure"]:
            failures_found += 1
        top_failures.append(
            {
                "type": evaluation["failure_type"],
                "severity": _severity_from_eval(evaluation),
                "h_sep_nm": evaluation["min_h_sep_nm"],
                "v_sep_ft": evaluation["min_v_sep_ft"],
                "description": (
                    f"Intruder at {int(state['int_altitude']):.0f} ft, "
                    f"crossing heading {int(state['int_heading']):.0f} deg"
                ),
                "distilled_target": round(float(row["distilled_target"]), 6),
                "teacher_prob": round(float(row["teacher_prob"]), 6),
                "quantum_score": round(float(row["quantum_score"]), 6),
                "scenario_type": evaluation["failure_type"],
            }
        )

    top_failures.sort(
        key=lambda item: (
            {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(item["severity"], 0),
            item["distilled_target"],
        ),
        reverse=True,
    )
    return top_failures[:10], failures_found, round(failures_found / max(candidate_budget, 1), 6)


def run_quantum_tree_pipeline(
    seed: int = 42,
    shots: int = 256,
    scenario_params: Optional[Dict[str, Any]] = None,
    fast: bool = False,
    output_path: Optional[str | Path] = "outputs/",
) -> Dict[str, Any]:
    effective_shots = 256 if fast else shots
    candidate_budget = 5 if fast else 50
    classical = run_classical_layer(seed=seed)
    quantum_layer = QuantumDistillationLayer(shots=effective_shots, seed=seed)
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
    top_failures, failures_found, failure_rate = _build_top_failures(
        distilled_rows=distilled_rows,
        scenario_params=scenario_params,
        candidate_budget=min(candidate_budget, len(distilled_rows)),
    )
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
        "run_id": f"qt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "architecture": [
            "Layer 1: classical teacher simulation with backpropagation",
            "Layer 2: quantum refinement layer using IBM Qiskit-compatible sampling",
            "Layer 3: distilled dataset used to train an autonomous student model",
        ],
        "scenario_params": scenario_params or {},
        "fast_mode": fast,
        "teacher_accuracy": float(summary["teacher_accuracy"]),
        "quantum_backend": str(summary["quantum_backend"]),
        "student_mse": float(summary["student_mse"]),
        "failures_found": failures_found,
        "failure_rate": failure_rate,
        "n_scenarios": min(candidate_budget, len(distilled_rows)),
        "summary": summary,
        "top_failures": top_failures,
        "top_distilled_states": ranked,
    }

    effective_output_path = None if fast else output_path
    if effective_output_path is not None:
        output_root = Path(effective_output_path)
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "quantum_tree_results.json").write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the QAA Quantum Tree distillation pipeline")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shots", type=int, default=256)
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    results = run_quantum_tree_pipeline(seed=args.seed, shots=args.shots, fast=args.fast)
    print("Quantum Tree distillation complete")
    print(f"Teacher accuracy : {results['summary']['teacher_accuracy']}")
    print(f"Quantum backend  : {results['summary']['quantum_backend']}")
    print(f"Student MSE      : {results['summary']['student_mse']}")
    if not args.fast:
        print(f"Results written  : {OUT / 'quantum_tree_results.json'}")


if __name__ == "__main__":
    main()
