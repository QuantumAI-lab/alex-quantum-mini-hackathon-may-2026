# Quantum Cybersecurity Challenge: Securing the Quantum Channel

A practical exploration of Quantum Key Distribution (QKD) using the BB84 protocol, developed for the **Quantum Cybersecurity Challenge**. This project provides a full end-to-end simulation of secure key exchange, eavesdropper detection, and secret key distillation using **IBM's Qiskit** framework.

## ðŸŒŸ The Three Core Pillars Implemented

### 1. Key Exchange
This simulation faithfully implements the **BB84 Protocol**. It models Alice preparing random bits encoded into quantum states (qubits) using randomly chosen bases ($Z$ or $X$). Bob then receives these qubits and measures them in his own randomly chosen bases.

### 2. Eavesdrop Detection
We simulate Eve performing an **Intercept-Resend Attack**. By attempting to measure the qubits in transit, Eve causes the quantum superposition states to collapse. The simulation measures the **Quantum Bit Error Rate (QBER)**. When Eve is active, the QBER reliably spikes to ~25%, crossing our predefined `11.0%` threshold, successfully catching the eavesdropper and aborting the session.

### 3. Secret Key Distillation
To convert raw exchanged bits into a usable cryptographic key, the project implements a complete classical post-processing pipeline:
- **Sifting:** Alice and Bob publicly share their chosen bases over a classical channel and discard mismatched bits.
- **Error Reconciliation:** A simulated 1-pass parity check (Biconf-style binary search) identifies and corrects natural errors introduced by hardware noise.
- **Privacy Amplification:** Using `SHA-256` hashing, the reconciled key is condensed into a perfectly secure, shorter key, mathematically eliminating any partial information Eve or the environment might possess.

---

## ðŸ› ï¸ Prerequisites

The project requires Python 3.8+ and relies on the following libraries:

- `qiskit` (Quantum Circuit Simulation)
- `qiskit-aer` (Aer Simulator for Noisy Quantum Channels)
- `numpy` (Mathematical arrays and random generation)

Install the dependencies using the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## ðŸš€ How to Run

To run the simulation and see the QKD process in action, simply execute the `main.py` script:

```bash
python main.py
```

### Simulation Scenarios
The `main.py` script automatically runs three distinct scenarios to validate the implementation:

1. **Ideal Channel:** A perfect quantum channel with no noise and no eavesdropper. Achieves 0% QBER.
2. **Noisy Hardware:** Simulates a realistic quantum environment with 3% depolarizing channel noise. The system handles the noise via error reconciliation and successfully distills a secure key.
3. **Eve Intercept-Resend Attack:** Simulates a man-in-the-middle attack. The system detects the anomalous QBER spike (~25%) and aborts the protocol to ensure complete security.

---

## ðŸ“‚ Codebase Documentation

### `qkd_bb84.py`
The core module containing the `BB84Simulation` class. 

- **`get_noise_model(error_prob)`**: Generates a Qiskit depolarizing noise model to simulate real-world hardware inaccuracies.
- **`execute_exchange(eve_present, error_prob)`**: Simulates the quantum channel. Handles Alice's state preparation using $X$ and $H$ gates, Eve's optional mid-air interception, and Bob's final measurements.
- **`sift_keys(...)`**: Performs the classical basis-matching phase to extract the raw key.
- **`calculate_qber(...)`**: Analyzes a subset of the sifted key to calculate the Quantum Bit Error Rate, ensuring channel integrity.
- **`error_reconciliation(...)`**: Applies a binary-search parity check algorithm to locate and fix bit errors caused by channel noise.
- **`privacy_amplification(...)`**: Applies SHA-256 cryptographic hashing to condense the key and output the final secure bitstring.

### `main.py`
The runner script. It instantiates the `BB84Simulation` and defines the `run_scenario` function, orchestrating the full 5-phase pipeline:
1. Quantum Exchange
2. Key Sifting
3. Security Analysis (QBER)
4. Error Reconciliation
5. Privacy Amplification

## ðŸ”¬ Theoretical Constraints (GLLP Bound)
The simulation incorporates elements of the GLLP security proof. During the Privacy Amplification phase, the final length of the secure key is determined dynamically using the binary entropy function $h(e)$ of the calculated QBER. The extractable secure fraction is conservatively bounded by `1 - 2*h(QBER)`.



## ðŸ‘¥ The Team

**Team Delta - Qsecurity**

*   **Team Members:**
    *   Anas Ahmed Hassan
    *   Anas Hesham Mahmoud
    *   Sief El Din Mohammed Mahmoud
    *   Omar El Shaer
*   **Team Mentors:**
    *   Muhammad Helmy / Sameh Zaghloul
---
