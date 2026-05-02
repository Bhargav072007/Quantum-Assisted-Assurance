"""
Layer 2: quantum refinement/distillation over classical teacher outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np

try:
    from qiskit import QuantumCircuit
    from qiskit.primitives import StatevectorSampler

    QISKIT_TREE_AVAILABLE = True
except ImportError:
    QuantumCircuit = None
    StatevectorSampler = None
    QISKIT_TREE_AVAILABLE = False


@dataclass
class QuantumDistillationLayer:
    """
    Converts teacher hidden activations into quantum-biased scores.
    """

    shots: int = 256
    seed: int = 42

    def _fallback_refine(self, hidden: np.ndarray, teacher_probs: np.ndarray) -> Dict[str, np.ndarray]:
        hidden_energy = np.mean(np.square(hidden), axis=1)
        hidden_energy = hidden_energy / max(np.max(hidden_energy), 1e-8)
        refined = 0.58 * teacher_probs + 0.42 * hidden_energy
        return {
            "backend": np.array(["classical-fallback"] * len(hidden), dtype=object),
            "quantum_scores": np.clip(refined, 0.0, 1.0),
        }

    def _qiskit_refine(self, hidden: np.ndarray, teacher_probs: np.ndarray) -> Dict[str, np.ndarray]:
        sampler = StatevectorSampler(seed=self.seed)
        quantum_scores = []
        backend = []
        for row, teacher_prob in zip(hidden, teacher_probs):
            qc = QuantumCircuit(3)
            features = np.abs(row[:3])
            scale = np.max(features) if np.max(features) > 0 else 1.0
            theta = np.clip(features / scale, 0.0, 1.0) * np.pi
            for qubit, angle in enumerate(theta):
                qc.ry(float(angle), qubit)
            qc.cz(0, 1)
            qc.cz(1, 2)
            qc.ry(float(np.clip(teacher_prob, 0.0, 1.0) * np.pi), 0)
            measured = qc.measure_all(inplace=False)
            result = sampler.run([measured], shots=self.shots).result()
            counts = result[0].data.meas.get_counts()
            weighted_ones = 0.0
            total = max(sum(counts.values()), 1)
            for bitstring, count in counts.items():
                weighted_ones += (bitstring.count("1") / 3.0) * count
            quantum_scores.append(weighted_ones / total)
            backend.append("qiskit-statevector")
        return {
            "backend": np.array(backend, dtype=object),
            "quantum_scores": np.clip(np.array(quantum_scores, dtype=float), 0.0, 1.0),
        }

    def refine(self, hidden: np.ndarray, teacher_probs: np.ndarray) -> Dict[str, np.ndarray]:
        if QISKIT_TREE_AVAILABLE:
            return self._qiskit_refine(hidden, teacher_probs)
        return self._fallback_refine(hidden, teacher_probs)
