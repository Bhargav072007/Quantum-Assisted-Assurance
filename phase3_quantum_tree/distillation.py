"""
Layer 3 prep: distill classical + quantum outputs into a student dataset.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np


def build_distilled_dataset(
    features: np.ndarray,
    states: List[Dict[str, float]],
    labels: np.ndarray,
    teacher_probs: np.ndarray,
    quantum_scores: np.ndarray,
) -> List[Dict[str, float]]:
    distilled_weight = 0.55 * teacher_probs + 0.45 * quantum_scores
    rows: List[Dict[str, float]] = []
    for index, state in enumerate(states):
        rows.append(
            {
                "int_heading": float(state["int_heading"]),
                "int_altitude": float(state["int_altitude"]),
                "int_speed": float(state["int_speed"]),
                "int_x_offset": float(state["int_x_offset"]),
                "feature_heading": float(features[index, 0]),
                "feature_altitude": float(features[index, 1]),
                "feature_speed": float(features[index, 2]),
                "feature_x_offset": float(features[index, 3]),
                "teacher_prob": float(teacher_probs[index]),
                "quantum_score": float(quantum_scores[index]),
                "distilled_target": float(distilled_weight[index]),
                "hard_label": float(labels[index]),
            }
        )
    return rows
