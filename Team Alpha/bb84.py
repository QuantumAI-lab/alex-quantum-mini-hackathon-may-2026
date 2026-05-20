import random
from utils import (
    random_bits, random_bases, calculate_qber,
    sift, reconcile, privacy_amplify,
    apply_channel_noise, bits_to_hex,
)
from quantum import bb84_prepare_and_measure


class BB84:
    def __init__(
        self,
        n_bits=1000,
        eve_present=False,
        eve_intercept_fraction=1.0,
        channel_error=0.0,
        qber_threshold=0.11,
        block_size=8,
        security_margin=8,
    ):
        self.n_bits = n_bits
        self.eve_present = eve_present
        self.eve_intercept_fraction = eve_intercept_fraction
        self.channel_error = channel_error
        self.qber_threshold = qber_threshold
        self.block_size = block_size
        self.security_margin = security_margin

    def _transmit(self, alice_bits, alice_bases, bob_bases):
        """
        Run the quantum transmission through real Qiskit circuits.
        For each qubit: Alice prepares, Eve optionally intercepts, Bob measures.
        Channel noise is applied as a classical bit-flip on Bob's outcome.
        """
        bob_bits = []
        for a_bit, a_basis, b_basis in zip(alice_bits, alice_bases, bob_bases):
            eve_basis = None
            if self.eve_present and random.random() < self.eve_intercept_fraction:
                eve_basis = random.choice(["Z", "X"])
            bob_bit, _eve_bit = bb84_prepare_and_measure(
                a_bit, a_basis, b_basis, eve_basis=eve_basis
            )
            if self.channel_error > 0 and random.random() < self.channel_error:
                bob_bit ^= 1
            bob_bits.append(bob_bit)
        return bob_bits

    def run(self):
        # --- Pillar 1: Key Exchange ---
        alice_bits  = random_bits(self.n_bits)
        alice_bases = random_bases(self.n_bits)
        bob_bases   = random_bases(self.n_bits)

        # --- Pillar 2: Eavesdrop Detection (Eve runs inside _transmit) ---
        bob_bits = self._transmit(alice_bits, alice_bases, bob_bases)

        sifted_alice, sifted_bob, sifted_idx = sift(
            alice_bits, alice_bases, bob_bits, bob_bases
        )

        # estimate QBER on a 10% random sample so those bits aren't in the final key
        sample_size = max(10, len(sifted_alice) // 10)
        sample_idx  = random.sample(range(len(sifted_alice)), min(sample_size, len(sifted_alice)))
        qber = calculate_qber(
            [sifted_alice[i] for i in sample_idx],
            [sifted_bob[i]   for i in sample_idx],
        )

        remaining_idx  = [i for i in range(len(sifted_alice)) if i not in set(sample_idx)]
        sifted_alice_r = [sifted_alice[i] for i in remaining_idx]
        sifted_bob_r   = [sifted_bob[i]   for i in remaining_idx]

        aborted = qber > self.qber_threshold

        # --- Pillar 3: Secret Key Distillation ---
        if aborted or not sifted_alice_r:
            reconciled_key, leaked_bits, final_key = [], 0, []
        else:
            reconciled_key, leaked_bits = reconcile(
                sifted_alice_r, sifted_bob_r, block_size=self.block_size
            )
            # privacy amplification driven by the measured QBER (Shor-Preskill)
            final_key = privacy_amplify(
                reconciled_key,
                leaked_bits=leaked_bits,
                qber=qber,
                security_margin=self.security_margin,
            )

        key_rate   = len(final_key) / self.n_bits
        efficiency = len(final_key) / len(sifted_alice_r) if sifted_alice_r else 0.0

        return {
            "raw_key":        alice_bits,
            "alice_bases":    alice_bases,
            "bob_bases":      bob_bases,
            "sifted_alice":   sifted_alice,
            "sifted_bob":     sifted_bob,
            "sifted_indices": sifted_idx,
            "qber":           qber,
            "aborted":        aborted,
            "reconciled_key": reconciled_key,
            "leaked_bits":    leaked_bits,
            "final_key":      final_key,
            "key_rate":       key_rate,
            "efficiency":     efficiency,
            "eve_present":    self.eve_present,
            "channel_error":  self.channel_error,
        }
