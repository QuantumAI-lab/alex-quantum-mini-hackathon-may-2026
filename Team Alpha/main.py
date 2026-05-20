from bb84 import BB84
from e91  import E91
from utils import bits_to_hex, print_section


def report(title, r, protocol="BB84"):
    print(f"\n  ▶  {title}")
    print(f"     Eve present       : {r['eve_present']}")
    print(f"     Channel noise     : {r['channel_error']:.1%}")
    print(f"     Sifted key length : {len(r['sifted_alice'])} bits")
    print(f"     QBER              : {r['qber']:.2%}")
    if protocol == "E91":
        sv = r["chsh_value"]
        print(f"     CHSH S-value      : {sv:.4f}  "
              f"(classical ≤ {r['chsh_classical_max']:.3f}, quantum ≤ {r['chsh_quantum_max']:.3f})")
    print(f"     Session aborted   : {r['aborted']}")
    if not r["aborted"]:
        print(f"     Reconciled length : {len(r['reconciled_key'])} bits  "
              f"(leaked {r['leaked_bits']} bits in parity)")
        print(f"     Final key length  : {len(r['final_key'])} bits")
        print(f"     Key rate          : {r['key_rate']:.4f} bits/raw-qubit")
        print(f"     Final key (hex)   : {bits_to_hex(r['final_key'])}")
    else:
        print(f"     ⚠  Session aborted — no key produced.")


# Pillar 1 + 3: BB84 clean run
print_section("PILLAR 1 + 3 · BB84 KEY EXCHANGE & DISTILLATION (no Eve)")
r = BB84(n_bits=2000, eve_present=False, channel_error=0.0).run()
report("BB84 — clean channel, no eavesdropper", r)
print(f"\n     Basis match rate  : {len(r['sifted_alice'])/len(r['raw_key']):.1%}  (expected ~50 %)")


# Pillar 2: Eve fully active
print_section("PILLAR 2 · BB84 EAVESDROP DETECTION (Eve fully active)")
r_no_eve   = BB84(n_bits=5000, eve_present=False).run()
r_with_eve = BB84(n_bits=5000, eve_present=True, eve_intercept_fraction=1.0).run()
report("BB84 — no Eve (reference)", r_no_eve)
report("BB84 — Eve intercepts ALL qubits", r_with_eve)
print(f"\n     QBER without Eve  : {r_no_eve['qber']:.2%}")
print(f"     QBER with Eve     : {r_with_eve['qber']:.2%}  (theory → ~25 % under full intercept-resend)")
print(f"     Abort threshold   : 11.00 %")
print(f"     Eve detected      : {r_with_eve['aborted']}")


# Pillar 2: QBER sweep over Eve fractions
print_section("PILLAR 2 · QBER SWEEP — Eve intercept fraction 0 %→100 %")
fractions = [0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]
print(f"\n  {'Eve fraction':>13}  {'QBER':>8}  {'Aborted':>8}  {'Final key len':>14}")
print(f"  {'-'*13}  {'-'*8}  {'-'*8}  {'-'*14}")
for f in fractions:
    r = BB84(n_bits=3000, eve_present=(f > 0), eve_intercept_fraction=f).run()
    print(f"  {f:>12.0%}  {r['qber']:>8.2%}  {'YES' if r['aborted'] else 'no':>8}  {len(r['final_key']):>14}")


# Stretch: noisy channel
print_section("STRETCH · NOISY CHANNEL — varying physical error rates")
print(f"\n  {'Channel noise':>14}  {'QBER':>8}  {'Aborted':>8}  {'Final key len':>14}")
print(f"  {'-'*14}  {'-'*8}  {'-'*8}  {'-'*14}")
for noise in [0.0, 0.01, 0.03, 0.05, 0.08, 0.10, 0.12]:
    r = BB84(n_bits=3000, eve_present=False, channel_error=noise).run()
    print(f"  {noise:>13.1%}  {r['qber']:>8.2%}  {'YES' if r['aborted'] else 'no':>8}  {len(r['final_key']):>14}")


# Stretch: E91 clean run
print_section("STRETCH · E91 KEY EXCHANGE & DISTILLATION (no Eve)")
r = E91(n_pairs=2000, eve_present=False).run()
report("E91 — clean channel, no eavesdropper", r, protocol="E91")
print(f"\n     CHSH S note: quantum mechanics predicts S ≈ 2√2 ≈ 2.828")
print(f"     Classical hidden variables can only reach S ≤ 2.0")
print(f"     Values between 2.0–2.828 confirm genuine entanglement.")


# Stretch: E91 with Eve
print_section("STRETCH · E91 EAVESDROP DETECTION (Eve destroys entanglement)")
r_no_eve   = E91(n_pairs=3000, eve_present=False).run()
r_with_eve = E91(n_pairs=3000, eve_present=True, eve_intercept_fraction=1.0).run()
report("E91 — no Eve (reference)", r_no_eve, protocol="E91")
report("E91 — Eve intercepts ALL pairs", r_with_eve, protocol="E91")
print(f"\n     CHSH without Eve : {r_no_eve['chsh_value']:.4f}")
print(f"     CHSH with Eve    : {r_with_eve['chsh_value']:.4f}  (collapses toward 2.0 — classical regime)")


# Stretch: protocol comparison
print_section("STRETCH · PROTOCOL COMPARISON — BB84 vs E91 (clean channel)")

def avg_key_rate(protocol_cls, kwargs, trials=5):
    rates = [protocol_cls(**kwargs).run()["key_rate"] for _ in range(trials)]
    return sum(rates) / len(rates)

bb84_rate = avg_key_rate(BB84, {"n_bits": 3000, "eve_present": False})
e91_rate  = avg_key_rate(E91,  {"n_pairs": 3000, "eve_present": False})

print(f"\n  {'Protocol':>10}  {'Avg key rate (bits/raw qubit)':>30}")
print(f"  {'-'*10}  {'-'*30}")
print(f"  {'BB84':>10}  {bb84_rate:>30.4f}")
print(f"  {'E91':>10}  {e91_rate:>30.4f}")
print(f"\n  BB84 sifts ~50% of bits; E91 uses only A0/B0 pairs for the key")
print(f"  (smaller fraction) but gets a built-in CHSH security certificate.\n")

print("=" * 60)
print("  ✓ Pillar 1 — Key Exchange (BB84 + E91)")
print("  ✓ Pillar 2 — Eavesdrop Detection (QBER + CHSH)")
print("  ✓ Pillar 3 — Secret Key Distillation (sift→reconcile→amplify)")
print("  ✓ Stretch  — Noisy channels, protocol comparison, key-rate sweep")
print("=" * 60)
