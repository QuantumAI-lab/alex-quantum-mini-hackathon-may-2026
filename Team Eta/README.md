# Team Eta Workspace
# 🧪 CO₂ Ground State Estimation — Alex Quantum Mini Hackathon (May 2026)

> Can a quantum computer figure out the energy of a CO₂ molecule?  
> That's exactly what we set out to answer.

---

## 💡 What Is This About?

Every molecule has a "ground state energy" — the lowest possible energy it can sit at, like the bottom of a valley. Knowing this number is useful for chemistry, materials science, and understanding how molecules behave.

The catch? Calculating it precisely gets incredibly hard as molecules get larger — even the fastest classical computers struggle. Quantum computers promise to help, but today's machines are still noisy and limited.

In this project we tackled **carbon dioxide (CO₂)** using a mix of quantum algorithms running on a simulator, and compared the results against a mathematically exact classical answer.

---

## ⚙️ How We Did It

We used **two different quantum approaches** and compared them side by side:

### 1. VQE — Variational Quantum Eigensolver
Think of this as a quantum-classical teamwork loop:
- The quantum computer tries out a "shape" for the molecule's quantum state
- A classical optimizer looks at the result and tweaks the shape to get a lower energy
- This repeats until the energy stops going down

We tested **5 different combinations** of circuit designs and optimization strategies:

| Method | Noiseless? | Final Error vs Exact |
|---|---|---|
| UCCSD + COBYLA | ✅ | 1.07 × 10⁻³ Ha |
| UCCSD + L-BFGS-B | ✅ | **6.31 × 10⁻⁵ Ha** ⭐ best |
| EfficientSU2 + COBYLA | ✅ | 6.83 × 10⁻² Ha |
| EfficientSU2 + SPSA | ✅ | 3.50 × 10⁻¹ Ha |
| EfficientSU2 + SPSA | ❌ noisy | 2.25 × 10⁻¹ Ha |

The chemistry-aware circuit (UCCSD) clearly outperformed the simpler hardware-efficient one.

### 2. SQD — Sample-Based Quantum Diagonalization
A newer approach (from IBM's *Nature* 2024 paper). Instead of optimizing in a loop:
- Use the best quantum state we already trained
- Sample it many times (like rolling a quantum dice)
- Take only the most frequent outcomes and solve a smaller, exact problem on those

More shots = more accuracy:

| Shots | Error vs Exact |
|---|---|
| 1,024 | 1.29 × 10⁻³ Ha |
| 4,096 | 8.11 × 10⁻⁵ Ha |
| 16,384 | **0.00** (matched exactly!) ✅ |
| 65,536 | **0.00** (matched exactly!) ✅ |

SQD hit the exact answer with just 16k samples — remarkable for how fast it runs.

---

## 📊 Key Numbers

| Quantity | Value |
|---|---|
| Molecule | CO₂ (linear, C-O bond = 1.16 Å) |
| Qubits needed | **6** |
| Exact (FCI) energy | −185.13712 Ha |
| Hartree-Fock energy | −185.06470 Ha |
| Best VQE result | −185.13706 Ha (UCCSD + L-BFGS-B) |
| Best SQD result | −185.13712 Ha (exact match ✅) |
| Chemical accuracy threshold | 1.6 × 10⁻³ Ha (1 kcal/mol) |

Both our best VQE run and SQD (at ≥4k shots) cleared the **chemical accuracy** bar — the standard benchmark for whether a result is useful in real chemistry.

---

## 📈 Figures

The notebook produces 4 plots saved to the `results/` folder:

| Figure | What it shows |
|---|---|
| `fig1_convergence.png` | How each VQE method's energy improved iteration by iteration |
| `fig2_accuracy_bars.png` | Final error of each VQE method on a log scale |
| `fig3_sqd_scaling.png` | How SQD accuracy improves as you take more samples |
| `fig4_summary.png` | All methods together vs the exact answer |

---

## 🛠️ How to Run It

### Requirements
- Python 3.9–3.11 (⚠️ not 3.12 — see note in notebook)
- Google Colab or a local Jupyter environment

### Steps

1. Open `co2_vqe_sqd_final_Output.ipynb` in Colab or Jupyter
2. Run **Cell 0** first — it installs the exact package versions needed
3. **Restart the kernel** when prompted
4. Run all remaining cells top to bottom

The notebook installs everything automatically — no manual setup needed.

### Packages used (pinned for compatibility)

```
qiskit            0.46.2
qiskit-aer        0.13.3
qiskit-algorithms 0.3.1
qiskit-nature     0.7.2
pyscf             ≥ 2.3
```

---

## 📁 Repository Structure

```
.
├── co2_vqe_sqd_final_Output.ipynb   # Main notebook (fully executed with outputs)
├── README.md                         # This file
└── results/
    ├── results.json                  # All numerical results
    ├── fig1_convergence.png
    ├── fig2_accuracy_bars.png
    ├── fig3_sqd_scaling.png
    └── fig4_summary.png
```

---

## 📚 Reference

Robledo-Moreno et al., *"Chemistry beyond exact solutions on a quantum-centric supercomputer"*, **Nature** (2024) — the paper that inspired the SQD approach used here.

---

*Submitted to the Alex Quantum Mini Hackathon — May 2026*
