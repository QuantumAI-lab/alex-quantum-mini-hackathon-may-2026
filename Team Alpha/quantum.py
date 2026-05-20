"""
quantum.py — Qiskit primitives for BB84 and E91.

Provides real quantum circuit-based operations:
    bb84_prepare_and_measure(alice_bit, alice_basis, bob_basis, eve_basis=None)
        -> (bob_bit, eve_bit_or_None)

    bell_pair_measure(alice_angle_deg, bob_angle_deg)
        -> (alice_bit, bob_bit)

Both functions build a small Qiskit circuit, simulate it via Statevector
sampling, and return classical bit outcomes. This keeps the bb84.py and
e91.py orchestration unchanged while moving the actual quantum mechanics
to genuine quantum circuits.

Basis convention (BB84):
    'Z' -> rectilinear (computational) basis, prep |0> or |1>
    'X' -> diagonal basis, prep |+> or |->
A qubit prepared in Z and measured in X (or vice versa) yields a uniformly
random outcome — this is what enforces the security of BB84.
"""

import math
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


# -------------------------------------------------------------------------
# BB84 prepare-and-measure
# -------------------------------------------------------------------------
def bb84_prepare_and_measure(alice_bit, alice_basis, bob_basis,
                              eve_basis=None):
    """
    Run one BB84 qubit through a real Qiskit circuit.

    Alice prepares (alice_bit, alice_basis). If eve_basis is given, Eve
    measures in that basis and resends in the same basis. Bob then
    measures in bob_basis.

    Returns (bob_bit, eve_bit) where eve_bit is None if eve_basis is None.

    Bases are 'Z' (rectilinear) or 'X' (diagonal).
    """
    # --- Alice prepares ---
    qc = QuantumCircuit(1)
    if alice_bit == 1:
        qc.x(0)
    if alice_basis == 'X':
        qc.h(0)
    state = Statevector.from_instruction(qc)

    eve_bit = None

    # --- Eve intercepts and re-sends ---
    if eve_basis is not None:
        # Rotate into Eve's measurement basis if X
        if eve_basis == 'X':
            qc_eve = QuantumCircuit(1)
            qc_eve.h(0)
            state = state.evolve(qc_eve)
        # Sample outcome from the diagonal probabilities
        probs = state.probabilities()
        eve_bit = 0 if _coin(probs[0]) else 1
        # Re-prepare a fresh qubit in eve_basis carrying eve_bit
        qc = QuantumCircuit(1)
        if eve_bit == 1:
            qc.x(0)
        if eve_basis == 'X':
            qc.h(0)
        state = Statevector.from_instruction(qc)

    # --- Bob measures ---
    if bob_basis == 'X':
        qc_bob = QuantumCircuit(1)
        qc_bob.h(0)
        state = state.evolve(qc_bob)
    probs = state.probabilities()
    bob_bit = 0 if _coin(probs[0]) else 1

    return bob_bit, eve_bit


# -------------------------------------------------------------------------
# E91 entangled-pair measurement
# -------------------------------------------------------------------------
def bell_pair_measure(alice_angle_deg, bob_angle_deg,
                       eve_intercepts=False):
    """
    Prepare a |Phi+> Bell pair (|00> + |11>)/sqrt(2). Measure Alice's qubit
    at alice_angle and Bob's at bob_angle.

    If eve_intercepts is True, Eve performs a basis measurement on each
    qubit (in the standard Z basis) and resends classical-correlated
    states — destroying the entanglement.

    Returns (alice_bit, bob_bit).
    """
    a_rad = math.radians(alice_angle_deg)
    b_rad = math.radians(bob_angle_deg)

    if eve_intercepts:
        # Eve measures both qubits in Z, then resends classical state.
        # The pre-measurement state is |Phi+>, so her measurement gives
        # 00 or 11 with equal probability — perfectly correlated bits.
        # She then resends |00> or |11>. Alice's and Bob's later
        # measurements at their chosen angles operate on a product state.
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        state = Statevector.from_instruction(qc)
        # Eve's Z-basis measurement on both qubits
        probs = state.probabilities()
        # probs indexed by integer 0..3 = |00>,|01>,|10>,|11>
        # for Phi+ only |00> and |11> have non-zero probability, each 0.5
        if _coin(probs[0] + probs[1]):
            eve_outcome = 0   # |00>
        else:
            eve_outcome = 3   # |11>
        # Resend product state with that outcome
        qc = QuantumCircuit(2)
        if eve_outcome == 3:
            qc.x(0)
            qc.x(1)
        state = Statevector.from_instruction(qc)
    else:
        # Honest Bell pair
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        state = Statevector.from_instruction(qc)

    # Rotate each qubit into its measurement basis.
    # Using Ry(-theta) gives correlation cos^2((a-b)/2) for matching outcomes
    # on |Phi+>, matching the polarization convention used elsewhere in the code.
    qc_rot = QuantumCircuit(2)
    qc_rot.ry(-a_rad, 0)
    qc_rot.ry(-b_rad, 1)
    state = state.evolve(qc_rot)

    # Joint probabilities over the four computational outcomes
    probs = state.probabilities()   # length 4: |a=0,b=0>, |a=1,b=0>, |a=0,b=1>, |a=1,b=1>
    # Qiskit convention: qubit 0 is least significant bit of the integer index.
    # So index = b*2 + a.
    p00 = probs[0]                          # a=0, b=0
    p10 = probs[1]                          # a=1, b=0
    p01 = probs[2]                          # a=0, b=1
    # p11 = probs[3]
    r = _rand01()
    if r < p00:
        return 0, 0
    if r < p00 + p10:
        return 1, 0
    if r < p00 + p10 + p01:
        return 0, 1
    return 1, 1


# -------------------------------------------------------------------------
# Small helpers — use the same `random` module the rest of the code uses
# so a single random.seed(...) controls reproducibility across modules.
# -------------------------------------------------------------------------
import random as _random


def _rand01():
    return _random.random()


def _coin(p_zero):
    """Return True with probability p_zero (outcome 0), else False."""
    return _random.random() < p_zero
