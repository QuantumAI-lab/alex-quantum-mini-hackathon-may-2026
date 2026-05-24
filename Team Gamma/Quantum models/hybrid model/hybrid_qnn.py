import os
import multiprocessing
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from qiskit import QuantumCircuit
from qiskit.circuit.library import ZZFeatureMap, RealAmplitudes
from qiskit_aer.primitives import EstimatorV2 as AerEstimator
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit_machine_learning.connectors import TorchConnector


# =============================================================================
# SECTION 1 — MODEL DEFINITIONS
# =============================================================================

class FeatureExtractor(nn.Module):
    """
    Classical pre-processing block.
    Maps raw tabular features → rotation angles in [0, π] for the quantum layer.
    Linear(input_dim→16) → ReLU → Dropout(0.2) → Linear(16→num_qubits) → Sigmoid×π
    """
    def __init__(self, input_dim: int, num_qubits: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, num_qubits),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.net(x)) * torch.pi  # output ∈ [0, π]


class HybridQNN(nn.Module):
    """
    Full hybrid model:
      FeatureExtractor → Quantum VQC layer → Linear output head
    TorchConnector makes the quantum layer fully differentiable,
    so the entire model trains end-to-end via standard backprop.
    """
    def __init__(self, extractor: nn.Module, quantum_layer: nn.Module):
        super().__init__()
        self.extractor     = extractor
        self.quantum_layer = quantum_layer
        self.out           = nn.Sequential(nn.Linear(1, 1), nn.Sigmoid())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.extractor(x)       
        x = self.quantum_layer(x)   
        return self.out(x)          


# =============================================================================
# SECTION 2 — QUANTUM CIRCUIT BUILDER
# =============================================================================

def build_quantum_layer(num_qubits: int, num_cores: int):
    """
    Builds a fresh VQC circuit on every call (required per fold to avoid
    parameter-sharing bugs across folds).

    Encoding : ZZFeatureMap (reps=1)
      - Single-qubit Rz(x_i) rotations per feature
      - ZZ entanglement: exp(-i·x_i·x_j·ZZ) for adjacent qubit pairs
      - Captures pairwise feature correlations in Hilbert space

    Ansatz   : RealAmplitudes (reps=2, linear entanglement)
      - Parameterised Ry rotations + CNOT ladder
      - Real parameters only → avoids barren plateau from complex phases
      - Linear entanglement → circuit depth O(n), not O(n²)

    Simulator: AerEstimator, statevector method
      - Exact expectation values, no shot noise → cleaner gradients
    """
    feature_map = ZZFeatureMap(feature_dimension=num_qubits, reps=1)
    ansatz      = RealAmplitudes(num_qubits=num_qubits, reps=2,
                                 entanglement='linear')

    qc = QuantumCircuit(num_qubits)
    qc.compose(feature_map, inplace=True)
    qc.compose(ansatz,      inplace=True)

    estimator = AerEstimator(
        options={
            "backend_options": {
                "device"                  : "CPU",
                "method"                  : "statevector",
                "max_parallel_threads"    : num_cores,
                "max_parallel_experiments": num_cores,
                "max_parallel_shots"      : num_cores,
            },
            "run_options": {"shots": None}  # exact statevector, no sampling
        }
    )

    qnn = EstimatorQNN(
        circuit=qc.decompose(reps=3),
        estimator=estimator,
        input_params=feature_map.parameters,
        weight_params=ansatz.parameters,
    )
    qnn.input_gradients = True

    return TorchConnector(qnn), feature_map, ansatz


def print_circuit_analysis(num_qubits, feature_map, ansatz):
    """Prints circuit complexity — required by Challenge criterion #2."""
    qc = QuantumCircuit(num_qubits)
    qc.compose(feature_map, inplace=True)
    qc.compose(ansatz,      inplace=True)
    qc = qc.decompose(reps=3)

    print("\n" + "─" * 52)
    print("  QUANTUM CIRCUIT ANALYSIS")
    print("─" * 52)
    print(f"  Qubits           : {num_qubits}")
    print(f"  Feature map      : ZZFeatureMap  (reps=1)")
    print(f"  Ansatz           : RealAmplitudes (reps=2, linear)")
    print(f"  Trainable params : {ansatz.num_parameters}")
    print(f"  Circuit depth    : {qc.depth()}")
    print(f"  Total gates      : {sum(qc.count_ops().values())}")
    print(f"  Gate breakdown   : {dict(qc.count_ops())}")
    print("─" * 52)


# =============================================================================
# SECTION 3 — MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':

    # ── Environment ───────────────────────────────────────────────────────────
    num_cores = multiprocessing.cpu_count()
    torch.set_num_threads(num_cores)
    os.environ["OMP_NUM_THREADS"] = str(num_cores)
    os.environ["MKL_NUM_THREADS"] = str(num_cores)
    print(f"Running on {num_cores} CPU cores")

    # ── A. Data Loading & Preprocessing ───────────────────────────────────────
    print("\n[1/3] Loading and preprocessing dataset...")
    df = pd.read_csv(r"E:\archive\dementia_dataset.csv")

    df['SES']   = df['SES'].fillna(df['SES'].median())
    df['MMSE']  = df['MMSE'].fillna(df['MMSE'].median())
    df['Group'] = df['Group'].map({'Nondemented': 0, 'Demented': 1, 'Converted': 1})
    df['M/F']   = df['M/F'].map({'M': 1, 'F': 0})
    df          = df.drop(['Subject ID', 'MRI ID', 'Hand'], axis=1)

    X = df.drop('Group', axis=1).values.astype(np.float32)
    y = df['Group'].values.astype(int)

    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    print(f"  Samples : {len(y)}  |  Features : {X.shape[1]}")
    print(f"  Classes : Non-demented={n_neg}, Demented={n_pos}")

    # ── B. Circuit Analysis ────────────────────────────────────────────────────
    print("\n[2/3] Analysing quantum circuit...")
    NUM_QUBITS  = 4
    _, fm, ans  = build_quantum_layer(NUM_QUBITS, num_cores)
    print_circuit_analysis(NUM_QUBITS, fm, ans)

    # ── C. 5-Fold Cross-Validation ─────────────────────────────────────────────
    print("\n[3/3] Running 5-Fold Cross-Validation (Hybrid QNN only)...")
    N_SPLITS   = 5
    EPOCHS     = 30
    skf        = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=42)
    pos_weight = torch.tensor([n_neg / n_pos], dtype=torch.float32)

    fold_metrics = {'accuracy': [], 'f1': [], 'auc': []}

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        print(f"\n{'═'*52}")
        print(f"  FOLD {fold+1}/{N_SPLITS}")
        print(f"{'═'*52}")

        # Scaler fit on train only — no data leakage
        scaler  = StandardScaler()
        X_tr    = scaler.fit_transform(X[train_idx])
        X_te    = scaler.transform(X[test_idx])
        y_tr    = y[train_idx]
        y_te    = y[test_idx]

        X_tr_t  = torch.tensor(X_tr, dtype=torch.float32)
        y_tr_t  = torch.tensor(y_tr, dtype=torch.float32)
        X_te_t  = torch.tensor(X_te, dtype=torch.float32)

        # num_workers=0 required on Windows in Jupyter/VS Code notebooks
        loader = DataLoader(
            TensorDataset(X_tr_t, y_tr_t),
            batch_size=64, shuffle=True, num_workers=0,
        )

        # Fresh quantum stack per fold
        q_layer, _, _  = build_quantum_layer(NUM_QUBITS, num_cores)
        extractor      = FeatureExtractor(X.shape[1], NUM_QUBITS)
        model          = HybridQNN(extractor, q_layer)
        optimizer      = optim.Adam(model.parameters(), lr=0.01)

        # ── Training ───────────────────────────────────────────────────────
        model.train()
        for epoch in range(EPOCHS):
            total_loss, n_batches = 0.0, 0
            for bx, by in loader:
                optimizer.zero_grad()
                preds = model(bx).squeeze()
                # Weighted BCE — compensates for class imbalance
                bce     = nn.functional.binary_cross_entropy(preds, by, reduction='none')
                weights = torch.where(by == 1, pos_weight, torch.ones_like(by))
                loss    = (bce * weights).mean()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                n_batches  += 1

            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1:>2}/{EPOCHS} | Avg Loss: {total_loss/n_batches:.4f}")

        # ── Evaluation ─────────────────────────────────────────────────────
        model.eval()
        with torch.no_grad():
            probs = model(X_te_t).squeeze().numpy()
        preds = (probs > 0.5).astype(int)

        acc = accuracy_score(y_te, preds)
        f1  = f1_score(y_te, preds, zero_division=0)
        auc = roc_auc_score(y_te, probs)

        fold_metrics['accuracy'].append(acc)
        fold_metrics['f1'].append(f1)
        fold_metrics['auc'].append(auc)

        print(f"\n  Fold {fold+1} Result → "
              f"Acc: {acc*100:.2f}%  F1: {f1:.4f}  AUC: {auc:.4f}")

    # ── Final Results ──────────────────────────────────────────────────────────
    acc = np.array(fold_metrics['accuracy'])
    f1  = np.array(fold_metrics['f1'])
    auc = np.array(fold_metrics['auc'])

    print("\n" + "═" * 52)
    print("  HYBRID QNN — FINAL RESULTS (5-Fold Avg)")
    print("═" * 52)
    print(f"  Accuracy : {acc.mean()*100:.2f}%  (+/- {acc.std()*100:.2f}%)")
    print(f"  F1-Score : {f1.mean():.4f}      (+/- {f1.std():.4f})")
    print(f"  AUC      : {auc.mean():.4f}      (+/- {auc.std():.4f})")
    print("═" * 52)
