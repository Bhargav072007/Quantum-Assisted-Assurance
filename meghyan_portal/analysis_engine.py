from __future__ import annotations

from typing import Any, Dict, List

from meghyan_portal.llm_service import generate_llm_response, llm_status


def estimate_tokens(prompt: str, metrics: Dict[str, Any]) -> int:
    base = 900
    prompt_cost = max(300, len(prompt.split()) * 42)
    context_cost = 700 if metrics.get("quantum_tree") else 250
    return base + prompt_cost + context_cost


def build_chart_points(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    comparison_summary = metrics.get("comparison", {}).get("summary", {})
    tree_summary = metrics.get("quantum_tree", {}).get("summary", {})
    qaoa_failures = int(comparison_summary.get("qaoa_unique_failures", 0) or 0)
    mc_failures = int(comparison_summary.get("mc_unique_failures", 0) or 0)
    teacher = float(tree_summary.get("teacher_accuracy", 0) or 0)
    student_mse = float(tree_summary.get("student_mse", 0) or 0)
    quantum_score = float(tree_summary.get("mean_quantum_score", 0) or 0)
    student_score = float(tree_summary.get("mean_student_score", 0) or 0)

    return [
        {"label": "Teacher", "value": round(teacher * 100, 1), "unit": "%"},
        {"label": "Quantum", "value": round(quantum_score * 100, 1), "unit": "%"},
        {"label": "Student", "value": round(student_score * 100, 1), "unit": "%"},
        {"label": "QAOA failures", "value": qaoa_failures, "unit": ""},
        {"label": "MC failures", "value": mc_failures, "unit": ""},
        {"label": "Student MSE", "value": round(student_mse * 1000, 2), "unit": "bp"},
    ]


def answer_question(prompt: str, metrics: Dict[str, Any], mode: str = "internal", history: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    llm_result = generate_llm_response(prompt, metrics, mode, history)
    chart_points = build_chart_points(metrics)
    recommendations = [
        "Run Quantum Tree before sharing any benchmark conclusion externally.",
        "Use analyst summaries for fast triage and queue formal verification for customer-facing evidence.",
        "Keep pricing on token usage for analysis and on credits for full assurance runs.",
    ]
    return {
        "answer": llm_result["answer"],
        "chart_points": chart_points,
        "recommendations": recommendations,
        "provider": llm_result["provider"],
        "model": llm_result["model"],
        "usage_tokens": llm_result.get("usage_tokens"),
        "llm_status": llm_status(),
        "mode": mode,
    }
