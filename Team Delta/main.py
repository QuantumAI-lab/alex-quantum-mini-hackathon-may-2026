import numpy as np
from qkd_bb84 import BB84Simulation

def run_scenario(name, num_qubits, eve_present, error_prob, qber_threshold=0.11):
    print(f"\\n{'='*50}")
    print(f"SCENARIO: {name}")
    print(f"Eve Present: {eve_present} | Channel Error Rate: {error_prob*100:.1f}%")
    print(f"{'='*50}")
    
    sim = BB84Simulation(num_qubits=num_qubits)
    
    # Phase 1: Exchange
    print("\\n[1] Quantum Exchange Phase...")
    alice_bits, alice_bases, bob_bits, bob_bases = sim.execute_exchange(
        eve_present=eve_present, 
        error_prob=error_prob
    )
    print(f"Raw bits exchanged: {num_qubits}")
    
    # Phase 2: Sifting
    print("\\n[2] Key Sifting Phase...")
    alice_sifted, bob_sifted = sim.sift_keys(alice_bits, alice_bases, bob_bits, bob_bases)
    print(f"Sifted key length: {len(alice_sifted)} bits")
    
    # Phase 3: QBER Calculation & Eavesdropper Detection
    print("\\n[3] Security Analysis (QBER)...")
    qber, alice_key, bob_key = sim.calculate_qber(alice_sifted, bob_sifted, sample_fraction=0.5)
    print(f"Estimated QBER: {qber*100:.2f}%")
    
    if qber > qber_threshold:
        print(f"!!! ALERT: QBER exceeds {qber_threshold*100}% threshold. Eavesdropper detected! Aborting protocol. !!!")
        return False
    else:
        print(f"Channel secure. Proceeding with key distillation...")
        
    # Phase 4: Error Reconciliation
    print("\\n[4] Error Reconciliation...")
    alice_recon, bob_recon = sim.error_reconciliation(alice_key, bob_key, block_size=8)
    errors_remaining = np.sum(alice_recon != bob_recon)
    print(f"Errors after reconciliation: {errors_remaining}")
    print(f"Reconciled key length: {len(alice_recon)} bits")
    
    # Phase 5: Privacy Amplification
    print("\\n[5] Privacy Amplification...")
    # Calculate final safe key length based on theoretical bounds (simplification)
    # GLLP bound says secret fraction is roughly: 1 - 2*h(QBER)
    def binary_entropy(p):
        if p == 0 or p == 1: return 0
        return -p * np.log2(p) - (1 - p) * np.log2(1 - p)
    
    h_qber = binary_entropy(qber)
    fraction = max(0.0, 1.0 - 2 * h_qber)
    final_length = int(len(alice_recon) * fraction)
    
    if final_length <= 0:
        print("Privacy amplification failed: No secure bits can be extracted.")
        return False
        
    final_key = sim.privacy_amplification(alice_recon, final_length)
    print(f"Final Secret Key Length: {len(final_key)} bits")
    print(f"Final Key Preview: {final_key[:16]}...")
    return True

if __name__ == "__main__":
    NUM_QUBITS = 1000
    
    # Scenario A: Ideal Channel, No Eve
    run_scenario("Ideal Channel", NUM_QUBITS, eve_present=False, error_prob=0.0)
    
    # Scenario B: Noisy Channel (e.g. thermal/optical noise), No Eve
    run_scenario("Noisy Hardware", NUM_QUBITS, eve_present=False, error_prob=0.03) # 3% hardware noise
    
    # Scenario C: Intercept-Resend Attack by Eve
    run_scenario("Eve Intercept-Resend Attack", NUM_QUBITS, eve_present=True, error_prob=0.0)
