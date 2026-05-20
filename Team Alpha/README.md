# Quantum Key Distribution — BB84 & E91

Simulates two QKD protocols end-to-end, covering all three core pillars and the stretch goals.

---

## Files

| File | What it does |
|---|---|
| `utils.py` | Bit/basis generation, QBER, sifting, reconciliation, privacy amplification |
| `quantum.py` | Qiskit primitives — BB84 prepare-and-measure and Bell-pair measurement |
| `bb84.py` | BB84 prepare-and-measure protocol |
| `e91.py` | E91 entanglement-based protocol with CHSH test |
| `main.py` | Runs 7 scenarios covering every pillar and stretch goal |
| `requirements.txt` | Dependencies |

---

## The Three Pillars

**1. Key Exchange**
- BB84: Alice encodes bits in random Z/X bases; Bob measures in random bases; matching positions become the raw key.
- E91: A Bell-pair source sends one qubit to each party; correlated measurements build the raw key.

**2. Eavesdrop Detection**
- BB84: Eve's intercept-resend attack pushes QBER toward ~25%. Session aborts above 11%.
- E91: Eve's interference collapses the CHSH S-value from ~2.83 (quantum) toward 2.0 (classical). Session aborts below S = 2.2.

**3. Secret Key Distillation**
1. Sifting — drop positions where bases didn't match.
2. Error reconciliation — parity-based Cascade (pass 1): Alice announces block parities, Bob locates and flips bad bits via binary search. Leaked bits are tracked.
3. Privacy amplification — SHA-256 hash compresses the key, removing whatever Eve might have learned from interception and reconciliation leakage.

---

## Stretch Goals

| Goal | Where |
|---|---|
| Noisy channel support | `apply_channel_noise()` in `utils.py`, scenario 4 in `main.py` |
| Protocol comparison | Scenario 7 in `main.py` |
| Key-rate metrics | `key_rate` and `efficiency` fields in every result dict |

---

## Run

```bash
pip install -r requirements.txt
python main.py
```

---

## Security Choices

- **QBER threshold 11%** — standard BB84 bound; above this Eve's information can't be bounded.
- **CHSH threshold 2.2** — well above the classical bound (2.0), leaving a safe margin.
- **Leakage tracking** — every parity bit Alice reveals is counted and subtracted during amplification.
- **SHA-256 amplification** — used as a practical universal-hash substitute, with output length bounded by the Shor-Preskill formula `n·(1 - h₂(QBER)) - leak_EC - 2·log₂(1/ε)`.
