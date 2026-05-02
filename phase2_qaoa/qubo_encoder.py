"""
QAA Phase 2 - QUBO encoder for 3D traffic separation exploration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

try:
    from qiskit.quantum_info import SparsePauliOp as QiskitSparsePauliOp
except ImportError:
    QiskitSparsePauliOp = None


PARAM_GRID: Dict[str, List[float]] = {
    "int_heading": [75.0, 90.0, 105.0, 120.0],
    "int_altitude": [28000.0, 30000.0, 31000.0, 32000.0],
    "int_speed": [3.0, 4.0, 5.0, 6.0],
    "int_x_offset": [-20.0, -10.0, 0.0, 10.0],
}

PARAM_ORDER: Sequence[str] = tuple(PARAM_GRID.keys())
N_QUBITS = 8


@dataclass(frozen=True)
class SimpleSparsePauliOp:
    """Small fallback used when Qiskit is unavailable locally."""

    terms: Tuple[Tuple[str, complex], ...]

    @classmethod
    def from_list(cls, terms: Iterable[Tuple[str, complex]]) -> "SimpleSparsePauliOp":
        return cls(tuple((label, complex(coeff)) for label, coeff in terms))

    @property
    def paulis(self) -> List[str]:
        return [label for label, _ in self.terms]

    @property
    def coeffs(self) -> np.ndarray:
        return np.array([coeff for _, coeff in self.terms], dtype=np.complex128)

    @property
    def num_qubits(self) -> int:
        return len(self.terms[0][0]) if self.terms else 0

    def __len__(self) -> int:
        return len(self.terms)

    def is_hermitian(self) -> bool:
        return all(abs(coeff.imag) < 1e-12 for _, coeff in self.terms)


SparsePauliOp = QiskitSparsePauliOp or SimpleSparsePauliOp


def _scale(value: float, min_value: float, max_value: float) -> float:
    if max_value == min_value:
        return 0.0
    return (value - min_value) / (max_value - min_value)


def estimate_failure_score(params: Dict[str, float]) -> float:
    """
    Returns a smooth 0-1 surrogate risk score for the paper's Phase 2 scenario.
    """
    heading = params["int_heading"]
    altitude = params["int_altitude"]
    speed = params["int_speed"]
    x_offset = params["int_x_offset"]

    heading_risk = max(0.0, 1.0 - abs(heading - 100.0) / 35.0)
    altitude_risk = max(0.0, 1.0 - abs(altitude - 31000.0) / 2500.0)
    speed_risk = _scale(speed, 3.0, 6.0)
    offset_risk = max(0.0, 1.0 - abs(x_offset) / 20.0)

    weighted = (
        0.34 * heading_risk
        + 0.30 * altitude_risk
        + 0.16 * speed_risk
        + 0.20 * offset_risk
    )
    interaction_bonus = 0.10 * heading_risk * altitude_risk * max(speed_risk, 0.25)
    return float(min(weighted + interaction_bonus, 1.0))


def decode_bitstring(bits: str) -> Dict[str, float]:
    """
    Decode an 8-bit QAOA output string to physical aviation parameters.
    Qiskit bitstrings are interpreted in reverse register order.
    """
    if len(bits) != N_QUBITS:
        raise ValueError(f"Expected {N_QUBITS} bits, received {len(bits)}")

    little_endian = bits[::-1]
    decoded: Dict[str, float] = {}
    for index, name in enumerate(PARAM_ORDER):
        upper = int(little_endian[index * 2])
        lower = int(little_endian[index * 2 + 1])
        value_index = (upper << 1) | lower
        decoded[name] = PARAM_GRID[name][value_index]
    return decoded


def encode_state_indices(indices: Sequence[int]) -> str:
    """Encodes parameter indices into a Qiskit-style bitstring."""
    if len(indices) != len(PARAM_ORDER):
        raise ValueError("Expected one index per parameter")

    little_endian = "".join(f"{value:02b}" for value in indices)
    return little_endian[::-1]


def enumerate_parameter_states() -> List[Dict[str, float]]:
    """Enumerates the full 4^4 Phase 2 design space."""
    states: List[Dict[str, float]] = []
    for heading in PARAM_GRID["int_heading"]:
        for altitude in PARAM_GRID["int_altitude"]:
            for speed in PARAM_GRID["int_speed"]:
                for x_offset in PARAM_GRID["int_x_offset"]:
                    states.append(
                        {
                            "int_heading": heading,
                            "int_altitude": altitude,
                            "int_speed": speed,
                            "int_x_offset": x_offset,
                        }
                    )
    return states


def build_qubo_matrix() -> np.ndarray:
    """
    Builds an 8x8 QUBO matrix. Diagonal terms encode per-bit risk preference and
    local pair couplings reward index combinations aligned with high-risk states.
    """
    qubo = np.zeros((N_QUBITS, N_QUBITS), dtype=float)
    bit_scores = np.zeros(N_QUBITS, dtype=float)
    pair_scores = np.zeros((N_QUBITS, N_QUBITS), dtype=float)
    states = enumerate_parameter_states()

    for state in states:
        score = estimate_failure_score(state)
        bits = encode_state_indices(
            [
                PARAM_GRID["int_heading"].index(state["int_heading"]),
                PARAM_GRID["int_altitude"].index(state["int_altitude"]),
                PARAM_GRID["int_speed"].index(state["int_speed"]),
                PARAM_GRID["int_x_offset"].index(state["int_x_offset"]),
            ]
        )[::-1]
        active = [index for index, bit in enumerate(bits) if bit == "1"]
        for bit_index in active:
            bit_scores[bit_index] += score
        for left in range(len(active)):
            for right in range(left + 1, len(active)):
                i = active[left]
                j = active[right]
                pair_scores[i, j] += score

    total_states = float(len(states))
    qubo[np.diag_indices(N_QUBITS)] = -(bit_scores / total_states)

    for i in range(N_QUBITS):
        for j in range(i + 1, N_QUBITS):
            qubo[i, j] = qubo[j, i] = -(pair_scores[i, j] / total_states) * 0.35

    for param_index in range(4):
        first = param_index * 2
        second = first + 1
        qubo[first, second] += 0.12
        qubo[second, first] += 0.12

    return qubo


def qubo_to_hamiltonian(qubo: np.ndarray) -> SparsePauliOp:
    """Converts a QUBO matrix into a diagonal Ising Hamiltonian."""
    num_qubits = qubo.shape[0]
    terms: List[Tuple[str, complex]] = []
    constant = 0.0

    for i in range(num_qubits):
        constant += qubo[i, i] / 2.0
        linear_coeff = -qubo[i, i] / 2.0
        if abs(linear_coeff) > 1e-12:
            label = "I" * (num_qubits - i - 1) + "Z" + "I" * i
            terms.append((label, complex(linear_coeff)))

    for i in range(num_qubits):
        for j in range(i + 1, num_qubits):
            q_value = (qubo[i, j] + qubo[j, i]) / 2.0
            if abs(q_value) <= 1e-12:
                continue
            constant += q_value / 4.0
            linear_i = -q_value / 4.0
            linear_j = -q_value / 4.0
            zz_coeff = q_value / 4.0

            label_i = "I" * (num_qubits - i - 1) + "Z" + "I" * i
            label_j = "I" * (num_qubits - j - 1) + "Z" + "I" * j
            zz_chars = list("I" * num_qubits)
            zz_chars[num_qubits - i - 1] = "Z"
            zz_chars[num_qubits - j - 1] = "Z"
            terms.extend(
                [
                    (label_i, complex(linear_i)),
                    (label_j, complex(linear_j)),
                    ("".join(zz_chars), complex(zz_coeff)),
                ]
            )

    terms.append(("I" * num_qubits, complex(constant)))
    return SparsePauliOp.from_list(terms)


def get_hamiltonian() -> Tuple[SparsePauliOp, np.ndarray]:
    qubo = build_qubo_matrix()
    return qubo_to_hamiltonian(qubo), qubo


if __name__ == "__main__":
    hamiltonian, qubo = get_hamiltonian()
    print("QAA - QUBO Encoder")
    print("=" * 32)
    print(f"QUBO matrix shape : {qubo.shape}")
    print(f"Hamiltonian terms : {len(hamiltonian)}")
    print(f"Num qubits        : {hamiltonian.num_qubits}")
    if hasattr(hamiltonian, "is_hermitian"):
        print(f"Hermitian         : {hamiltonian.is_hermitian()}")
    sample = decode_bitstring("01101001")
    print("Sample decode     :", sample)
