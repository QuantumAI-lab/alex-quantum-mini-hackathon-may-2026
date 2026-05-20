import random
import math
from utils import (
    calculate_qber,
    reconcile, privacy_amplify,
    bits_to_hex,
)
from quantum import bell_pair_measure

# Alice measures at 0° or 45°, Bob at 22.5° or 67.5°.
# These angles produce a CHSH value of ~2.39 — well above the classical
# bound of 2.0, confirming genuine entanglement. The absolute quantum
# maximum 2√2 ≈ 2.83 requires angles (0°, 90°) and (45°, 135°), but
# 2.39 is comfortably sufficient as a Bell-violation security certificate.
ALICE_ANGLES = [0.0, 45.0]
BOB_ANGLES   = [22.5, 67.5]


def _measure_entangled_pair(alice_angle_deg, bob_angle_deg,
                             eve_present, eve_fraction, channel_error):
    # Eve intercepts a fraction of pairs. When she does, she measures both
    # qubits and resends a classical product state — destroying entanglement.
    eve_intercepts = eve_present and random.random() < eve_fraction

    # Real Qiskit Bell-pair measurement
    alice_bit, bob_bit = bell_pair_measure(
        alice_angle_deg, bob_angle_deg, eve_intercepts=eve_intercepts
    )

    if channel_error > 0 and random.random() < channel_error:
        bob_bit ^= 1

    return alice_bit, bob_bit


def _chsh_expectation(a_bits, b_bits):
    if not a_bits:
        return 0.0
    agree    = sum(a == b for a, b in zip(a_bits, b_bits))
    disagree = len(a_bits) - agree
    return (agree - disagree) / len(a_bits)


class E91:
    CHSH_QUANTUM_MAX   = 2 * math.sqrt(2)  # ~2.828
    CHSH_CLASSICAL_MAX = 2.0

    def __init__(
        self,
        n_pairs=1000,
        eve_present=False,
        eve_intercept_fraction=1.0,
        channel_error=0.0,
        qber_threshold=0.11,
        chsh_threshold=2.2,
        block_size=8,
        security_margin=8,
    ):
        self.n_pairs                = n_pairs
        self.eve_present            = eve_present
        self.eve_intercept_fraction = eve_intercept_fraction
        self.channel_error          = channel_error
        self.qber_threshold         = qber_threshold
        self.chsh_threshold         = chsh_threshold
        self.block_size             = block_size
        self.security_margin        = security_margin

    def run(self):
        alice_basis_idx = [random.randint(0, 1) for _ in range(self.n_pairs)]
        bob_basis_idx   = [random.randint(0, 1) for _ in range(self.n_pairs)]

        alice_bits_all, bob_bits_all = [], []
        chsh_buckets = {(0,0):([], []), (0,1):([], []), (1,0):([], []), (1,1):([], [])}

        for ai, bi in zip(alice_basis_idx, bob_basis_idx):
            a_bit, b_bit = _measure_entangled_pair(
                ALICE_ANGLES[ai], BOB_ANGLES[bi],
                self.eve_present, self.eve_intercept_fraction, self.channel_error,
            )
            alice_bits_all.append(a_bit)
            bob_bits_all.append(b_bit)
            chsh_buckets[(ai, bi)][0].append(a_bit)
            chsh_buckets[(ai, bi)][1].append(b_bit)

        # CHSH: S = E(A0,B0) - E(A0,B1) + E(A1,B0) + E(A1,B1)
        e00 = _chsh_expectation(*chsh_buckets[(0, 0)])
        e01 = _chsh_expectation(*chsh_buckets[(0, 1)])
        e10 = _chsh_expectation(*chsh_buckets[(1, 0)])
        e11 = _chsh_expectation(*chsh_buckets[(1, 1)])
        chsh_value = abs(e00 - e01 + e10 + e11)

        # Key bits come from the A0/B0 basis pair
        sifted_alice = [alice_bits_all[i] for i, (ai, bi) in enumerate(zip(alice_basis_idx, bob_basis_idx)) if ai == 0 and bi == 0]
        sifted_bob   = [bob_bits_all[i]   for i, (ai, bi) in enumerate(zip(alice_basis_idx, bob_basis_idx)) if ai == 0 and bi == 0]

        sample_size = max(10, len(sifted_alice) // 10)
        sample_idx  = random.sample(range(len(sifted_alice)), min(sample_size, len(sifted_alice)))
        qber = calculate_qber(
            [sifted_alice[i] for i in sample_idx],
            [sifted_bob[i]   for i in sample_idx],
        )

        remaining_idx  = [i for i in range(len(sifted_alice)) if i not in set(sample_idx)]
        sifted_alice_r = [sifted_alice[i] for i in remaining_idx]
        sifted_bob_r   = [sifted_bob[i]   for i in remaining_idx]

        aborted = (qber > self.qber_threshold) or (chsh_value < self.chsh_threshold)

        if aborted or not sifted_alice_r:
            reconciled_key, leaked_bits, final_key = [], 0, []
        else:
            reconciled_key, leaked_bits = reconcile(
                sifted_alice_r, sifted_bob_r, block_size=self.block_size
            )
            final_key = privacy_amplify(
                reconciled_key,
                leaked_bits=leaked_bits,
                qber=qber,
                security_margin=self.security_margin,
            )

        return {
            "alice_bits":         alice_bits_all,
            "bob_bits":           bob_bits_all,
            "alice_basis_idx":    alice_basis_idx,
            "bob_basis_idx":      bob_basis_idx,
            "sifted_alice":       sifted_alice,
            "sifted_bob":         sifted_bob,
            "chsh_value":         chsh_value,
            "chsh_quantum_max":   self.CHSH_QUANTUM_MAX,
            "chsh_classical_max": self.CHSH_CLASSICAL_MAX,
            "qber":               qber,
            "aborted":            aborted,
            "reconciled_key":     reconciled_key,
            "leaked_bits":        leaked_bits,
            "final_key":          final_key,
            "key_rate":           len(final_key) / self.n_pairs,
            "efficiency":         len(final_key) / len(sifted_alice_r) if sifted_alice_r else 0.0,
            "eve_present":        self.eve_present,
            "channel_error":      self.channel_error,
        }
