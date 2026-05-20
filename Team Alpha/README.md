# Quantum Key Distribution — BB84 & E91

A full simulation of two quantum key distribution protocols, built in Python with real quantum circuits via Qiskit. Covers key exchange, eavesdrop detection, and secret key distillation — all three core pillars — plus noisy channel modelling, protocol comparison, and key-rate analysis as stretch goals.

---

## The Problem

Classical key exchange (e.g. Diffie-Hellman, RSA) depends on computational hardness assumptions. A sufficiently powerful quantum computer running Shor's algorithm breaks both. We need a way to distribute secret keys whose security is guaranteed by the laws of physics, not by the difficulty of a math problem.

**The core challenge: how do two parties (Alice and Bob) agree on a shared secret key over a public channel, while being able to detect if anyone is listening?**

Quantum mechanics gives us the answer through two properties:

- **No-cloning theorem** — an unknown quantum state cannot be copied perfectly. Any eavesdropper must disturb the qubits they intercept.
- **Measurement collapse** — measuring a qubit in the wrong basis destroys the original state and introduces detectable errors.

This project implements and demonstrates two protocols that exploit these properties: **BB84** (prepare-and-measure) and **E91** (entanglement-based).

---

## The Solution — Three Pillars

### Pillar 1 · Key Exchange

**BB84 (Bennett & Brassard, 1984)**

Alice picks a random bit and a random basis (Z = rectilinear, X = diagonal) for each qubit she sends. Bob independently picks a random basis to measure each qubit. After transmission, they publicly announce their *bases* (not their bits). They keep only the positions where their bases matched — the sifted key. About 50% of bits survive sifting.

```
Alice bit:   0   1   1   0   1   0   0   1
Alice basis: Z   X   Z   X   Z   X   X   Z
Bob basis:   Z   Z   Z   X   X   X   X   Z
             ✓   ✗   ✓   ✓   ✗   ✓   ✓   ✓   ← basis match?
Sifted key:  0       1   0       0   0   1
```

**E91 (Ekert, 1991)**

A source emits entangled Bell pairs (|Φ+⟩ = (|00⟩+|11⟩)/√2). Alice receives one qubit, Bob the other. Each independently picks a measurement angle. Positions where both chose the A0/B0 angle pair become the raw key; the other angle combinations feed a CHSH security test.

Both protocols use **real Qiskit quantum circuits** (`quantum.py`) — Qiskit's `Statevector` simulator handles the actual quantum mechanics, not just classical coin flips.

---

### Pillar 2 · Eavesdrop Detection

**BB84 — QBER threshold**

Eve performs an intercept-resend attack: she measures each qubit in a random basis and re-sends a fresh qubit toward Bob. When she guesses the wrong basis (~50% of the time) she introduces an error. The **Quantum Bit Error Rate** rises to ~25% under a full attack.

```
No Eve:    QBER ≈  0–2%   → session continues
Eve 30%:   QBER ≈  7–8%   → session continues (Eve partially detected)
Eve 50%+:  QBER ≈ 12–14%  → session ABORTED
Eve 100%:  QBER ≈  25%    → session ABORTED
```

If QBER exceeds **11%** (the standard BB84 security bound), Alice and Bob abort — no key is produced.

**E91 — CHSH inequality test**

Genuine entanglement produces correlations that violate the CHSH inequality. The S-value for |Φ+⟩ at the chosen angles sits around **2.4**, well above the classical bound of **2.0**. When Eve intercepts qubits she destroys the entanglement, and S collapses toward 2.0.

```
No Eve:  S ≈ 2.4  → genuine entanglement confirmed, session continues
Eve:     S ≈ 0.1  → entanglement destroyed, session ABORTED
```

The session aborts if S < **2.2** or QBER > 11%, whichever triggers first.

---

### Pillar 3 · Secret Key Distillation

Even after eavesdrop detection passes, the sifted key may still have errors from channel noise or partial Eve activity. Three steps turn it into a final secure key:

**Step 1 — Sifting** (done in Pillar 1)
Discard positions where Alice and Bob used different bases.

**Step 2 — Error Reconciliation**
Single-pass Cascade-style binary parity. Alice announces the XOR parity of non-overlapping blocks. For any block where Bob's parity disagrees, a binary search locates and flips the erroneous bit. Every parity announcement leaks one bit of information to Eve, so each leaked bit is counted precisely.

```
Block size 8 → Alice announces 1 parity bit per block (1 bit leaked)
Binary search → up to 3 additional parity bits per bad block
All leakage is tracked and removed in the next step.
```

**Step 3 — Privacy Amplification**
The reconciled key is compressed using SHA-256. Output length is determined by the Shor-Preskill formula:

```
L = n × (1 - h₂(QBER)) - leak_EC - 2 × log₂(1/ε)
```

where `h₂` is binary entropy and `ε = 10⁻¹⁰` is the security parameter. This removes Eve's partial knowledge accumulated from both interception and reconciliation leakage, producing the **final shared secret key**.

---

## Stretch Goals

| Goal | Implementation |
|---|---|
| Noisy channel | `apply_channel_noise()` in `utils.py` — independently flips bits at a configurable rate, modelling real fiber/free-space losses |
| Protocol comparison | Scenario 7 in `main.py` — 5-trial average key rate for BB84 vs E91 |
| Key-rate metrics | Every result dict includes `key_rate` (final bits / raw qubits) and `efficiency` (final bits / sifted bits) |
| Real quantum circuits | `quantum.py` — genuine Qiskit `QuantumCircuit` objects, not classical approximations |

---

## File Structure

```
.
├── main.py          — entry point; runs all 7 demonstration scenarios
├── bb84.py          — BB84 protocol orchestration
├── e91.py           — E91 protocol orchestration
├── quantum.py       — Qiskit circuits for BB84 and E91 measurements
├── utils.py         — sifting, reconciliation, privacy amplification, QBER, helpers
├── requirements.txt — dependencies (qiskit>=1.0, numpy)
└── README.md        — this file
```

### How the files connect

```
main.py
  ├── BB84  (bb84.py)
  │     ├── bb84_prepare_and_measure()  ←  quantum.py  (Qiskit circuit)
  │     └── sift / reconcile / privacy_amplify  ←  utils.py
  └── E91   (e91.py)
        ├── bell_pair_measure()  ←  quantum.py  (Qiskit Bell-pair circuit)
        └── calculate_qber / reconcile / privacy_amplify  ←  utils.py
```

---

## Setup & Run

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
python main.py
```

> **Speed note:** E91 runs a real Qiskit Statevector circuit per entangled pair. With `n_pairs=2000` this takes a few seconds per scenario. Reduce `n_pairs` to 300–500 if you just want a quick test.

---

## Sample Output

```
============================================================
  PILLAR 2 · QBER SWEEP — Eve intercept fraction 0 %→100 %
============================================================

   Eve fraction      QBER   Aborted   Final key len
  -------------  --------  --------  --------------
            0%     0.00%        no             189
           10%     1.32%        no             171
           20%     4.05%        no             143
           30%    11.56%       YES               0
           50%    13.38%       YES               0
           75%    20.26%       YES               0
          100%    24.77%       YES               0

============================================================
  STRETCH · E91 EAVESDROP DETECTION
============================================================

  ▶  E91 — no Eve (reference)
     CHSH S-value      : 2.4308  (classical ≤ 2.000, quantum ≤ 2.828)
     QBER              : 1.96%
     Session aborted   : False
     Final key length  : 256 bits

  ▶  E91 — Eve intercepts ALL pairs
     CHSH S-value      : 0.0947  (classical ≤ 2.000, quantum ≤ 2.828)
     QBER              : 43.84%
     Session aborted   : True
     ⚠  Session aborted — no key produced.

============================================================
  ✓ Pillar 1 — Key Exchange (BB84 + E91)
  ✓ Pillar 2 — Eavesdrop Detection (QBER + CHSH)
  ✓ Pillar 3 — Secret Key Distillation (sift→reconcile→amplify)
  ✓ Stretch  — Noisy channels, protocol comparison, key-rate sweep
============================================================
```

---

## Security Parameters

| Parameter | Value | Reason |
|---|---|---|
| QBER abort threshold | 11% | Standard BB84 bound — above this Eve's information cannot be bounded |
| CHSH abort threshold | S < 2.2 | Conservative margin above the classical bound (2.0) |
| Privacy amplification ε | 10⁻¹⁰ | Security parameter driving how aggressively the key is compressed |
| Reconciliation block size | 8 bits | Smaller blocks fix more errors but leak more parity bits |
| Security margin | 8 bits | Additional buffer subtracted from final key length |

---

## Design Decisions & Tradeoffs

**Why SHA-256 for privacy amplification?**
The provably secure choice is a Toeplitz matrix (a 2-universal hash family), which gives a full information-theoretic guarantee. SHA-256 is used here as a practical substitute — acceptable for simulation, but not for a certified real-device deployment.

**Why sample only 10% of sifted bits for QBER?**
The bits used to estimate QBER are publicly compared and must be discarded. Using 10% preserves 90% of the sifted key for actual key material, balancing estimate accuracy against key length.

**Why does E91 produce a lower key rate than BB84?**
BB84 keeps ~50% of raw bits after sifting. E91 uses only the A0/B0 angle pair for key bits (~25% of pairs) and spends the rest on the CHSH test. The security certificate costs throughput.

**Why doesn't the CHSH S-value reach the theoretical maximum of 2√2 ≈ 2.828?**
The angles {0°, 45°} for Alice and {22.5°, 67.5°} for Bob produce a theoretical S ≈ 2.39 for |Φ+⟩, not the absolute maximum. Reaching 2√2 requires a different state (|Ψ−⟩) and angle set. The chosen angles are standard in the literature and give a clear, unambiguous Bell violation.
