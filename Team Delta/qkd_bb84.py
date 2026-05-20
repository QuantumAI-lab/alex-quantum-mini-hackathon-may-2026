import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
import hashlib

class BB84Simulation:
    def __init__(self, num_qubits=1000):
        self.num_qubits = num_qubits
        self.simulator = AerSimulator()
        
    def get_noise_model(self, error_prob=0.0):
        """Creates a depolarizing noise model."""
        if error_prob <= 0.0:
            return None
        noise_model = NoiseModel()
        # Single qubit depolarizing error
        error = depolarizing_error(error_prob, 1)
        noise_model.add_all_qubit_quantum_error(error, ['x', 'h', 'id'])
        return noise_model

    def execute_exchange(self, eve_present=False, error_prob=0.0):
        """Phase 1 & 2: Alice prepares, Eve optionally intercepts, Bob measures."""
        alice_bits = np.random.randint(2, size=self.num_qubits)
        alice_bases = np.random.randint(2, size=self.num_qubits)
        
        eve_bases = np.random.randint(2, size=self.num_qubits) if eve_present else None
        
        bob_bases = np.random.randint(2, size=self.num_qubits)
        bob_bits = np.zeros(self.num_qubits, dtype=int)
        
        noise_model = self.get_noise_model(error_prob)
        
        for i in range(self.num_qubits):
            # Create a circuit with 1 qubit and 2 classical bits (if Eve present) or 1 (if not)
            qc = QuantumCircuit(1, 2 if eve_present else 1)
            
            # --- ALICE ---
            if alice_bits[i] == 1:
                qc.x(0)
            if alice_bases[i] == 1:
                qc.h(0)
                
            # --- EVE ---
            if eve_present:
                if eve_bases[i] == 1:
                    qc.h(0)
                qc.measure(0, 0) # Eve measures to classical bit 0
                
                # Intercept-Resend: state has collapsed, re-apply basis
                if eve_bases[i] == 1:
                    qc.h(0)
                    
            # --- BOB ---
            if bob_bases[i] == 1:
                qc.h(0)
                
            meas_bit = 1 if eve_present else 0
            qc.measure(0, meas_bit) # Bob measures to classical bit 1 (or 0 if no Eve)
            
            # Simulate the circuit
            result = self.simulator.run(qc, shots=1, noise_model=noise_model).result()
            counts = result.get_counts()
            
            # Parse outcome
            outcome = list(counts.keys())[0]
            # In Qiskit, bitstrings are read right-to-left within a register. 
            # If 2 classical bits, outcome is '10' where outcome[0] is c1 (Bob) and outcome[1] is c0 (Eve).
            # If 1 classical bit, outcome is '0' where outcome[0] is c0.
            if eve_present:
                bob_bit_str = outcome[0] # Bob's bit (c1)
            else:
                bob_bit_str = outcome[0]
                
            bob_bits[i] = int(bob_bit_str)
            
        return alice_bits, alice_bases, bob_bits, bob_bases

    def sift_keys(self, alice_bits, alice_bases, bob_bits, bob_bases):
        """Phase 3a: Discard bits where bases don't match."""
        matching_bases = (alice_bases == bob_bases)
        alice_sifted = alice_bits[matching_bases]
        bob_sifted = bob_bits[matching_bases]
        return alice_sifted, bob_sifted

    def calculate_qber(self, alice_sifted, bob_sifted, sample_fraction=0.5):
        """Phase 3b: Reveal a portion of the sifted key to estimate error rate."""
        sample_size = int(len(alice_sifted) * sample_fraction)
        
        alice_sample = alice_sifted[:sample_size]
        bob_sample = bob_sifted[:sample_size]
        
        errors = np.sum(alice_sample != bob_sample)
        qber = errors / sample_size if sample_size > 0 else 1.0
        
        # Return QBER and the unrevealed portion of the key
        return qber, alice_sifted[sample_size:], bob_sifted[sample_size:]

    def error_reconciliation(self, alice_key, bob_key, block_size=8):
        """Phase 3c: Correct errors in Bob's key using a simplified 1-pass parity check (Biconf)."""
        corrected_bob_key = bob_key.copy()
        
        def correct_block(start, end):
            if end - start == 1:
                corrected_bob_key[start] ^= 1 # Flip bit
                return
                
            mid = (start + end) // 2
            
            alice_parity = np.sum(alice_key[start:mid]) % 2
            bob_parity = np.sum(corrected_bob_key[start:mid]) % 2
            
            if alice_parity != bob_parity:
                correct_block(start, mid)
            else:
                correct_block(mid, end)

        n_blocks = len(alice_key) // block_size
        alice_key = alice_key[:n_blocks*block_size]
        corrected_bob_key = corrected_bob_key[:n_blocks*block_size]
        
        final_alice = []
        final_bob = []
        
        for i in range(n_blocks):
            start = i * block_size
            end = start + block_size
            
            alice_parity = np.sum(alice_key[start:end]) % 2
            bob_parity = np.sum(corrected_bob_key[start:end]) % 2
            
            if alice_parity != bob_parity:
                correct_block(start, end)
                
            # Discard 1 bit per block to compensate for parity information revealed
            final_alice.extend(alice_key[start:end-1])
            final_bob.extend(corrected_bob_key[start:end-1])
            
        return np.array(final_alice), np.array(final_bob)

    def privacy_amplification(self, key, final_length):
        """Phase 3d: Hash the key to reduce Eve's potential information to practically zero."""
        if len(key) == 0 or final_length <= 0:
            return np.array([])
            
        key_bytes = np.packbits(key).tobytes()
        hash_obj = hashlib.sha256(key_bytes)
        hash_bytes = hash_obj.digest()
        
        hash_bits = np.unpackbits(np.frombuffer(hash_bytes, dtype=np.uint8))
        return hash_bits[:final_length]
