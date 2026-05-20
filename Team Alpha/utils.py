"""
utils.py — reconstructed to match the imports in bb84.py / e91.py / main.py.

Required API:
    random_bits(n)               -> list[int] of length n
    random_bases(n)              -> list[str] of length n, each 'Z' or 'X'
    calculate_qber(a, b)         -> float
    sift(alice_bits, alice_bases, bob_bits, bob_bases) -> (sa, sb, idx)
    reconcile(a, b, block_size)  -> (corrected_key, leaked_bits)
    privacy_amplify(key, leaked_bits, eve_bits, security_margin) -> list[int]
    apply_channel_noise(bits, p) -> list[int]
    bits_to_hex(bits)            -> str
    print_section(title)         -> None
"""
import random
import hashlib


def random_bits(n):
    return [random.randint(0, 1) for _ in range(n)]


def random_bases(n):
    return [random.choice(["Z", "X"]) for _ in range(n)]


def calculate_qber(a, b):
    if not a:
        return 0.0
    errors = sum(x != y for x, y in zip(a, b))
    return errors / len(a)


def sift(alice_bits, alice_bases, bob_bits, bob_bases):
    sa, sb, idx = [], [], []
    for i in range(len(alice_bits)):
        if alice_bases[i] == bob_bases[i]:
            sa.append(alice_bits[i])
            sb.append(bob_bits[i])
            idx.append(i)
    return sa, sb, idx


def apply_channel_noise(bits, p):
    return [b ^ 1 if random.random() < p else b for b in bits]


def _parity(block):
    p = 0
    for b in block:
        p ^= b
    return p


def reconcile(alice_key, bob_key, block_size=8):
    """
    Single-pass Cascade-style block parity reconciliation with binary search.
    Returns (corrected_bob_key, leaked_bits_count).
    """
    if len(alice_key) != len(bob_key):
        raise ValueError("keys must have equal length")
    a = list(alice_key)
    b = list(bob_key)
    n = len(a)
    leaked = 0
    for start in range(0, n, block_size):
        end = min(start + block_size, n)
        # Alice discloses parity of her block -> 1 bit leaked
        leaked += 1
        if _parity(a[start:end]) == _parity(b[start:end]):
            continue
        # Binary search to locate the single odd error in this block
        lo, hi = start, end
        while hi - lo > 1:
            mid = (lo + hi) // 2
            leaked += 1
            if _parity(a[lo:mid]) != _parity(b[lo:mid]):
                hi = mid
            else:
                lo = mid
        b[lo] ^= 1
    # Cascade returns Alice's key (Bob's is now corrected to match it)
    return a, leaked


def privacy_amplify(key, leaked_bits=0, eve_bits=0, security_margin=8,
                    qber=0.0, epsilon_pa=1e-10):
    """
    Privacy amplification using the Shor-Preskill bound and the leftover
    hash lemma.

    Output length L = n*(1 - h2(qber)) - leaked_bits - 2*log2(1/epsilon_pa)

    Note: SHA-256 is not a 2-universal hash family, so this is a practical
    stand-in. A Toeplitz matrix would give a true information-theoretic
    guarantee. The eve_bits and security_margin arguments are retained for
    backwards compatibility but no longer drive the formula directly:
    eve_bits is folded into qber if qber=0 was passed, and security_margin
    is replaced by 2*log2(1/epsilon_pa).
    """
    import math
    n = len(key)
    if n == 0:
        return []

    # Backwards-compat: if caller didn't pass qber, infer one from eve_bits
    if qber == 0.0 and eve_bits > 0:
        qber = eve_bits / n

    # Binary entropy h2(p)
    def _h2(p):
        if p <= 0.0 or p >= 1.0:
            return 0.0
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

    pa_security = 2 * math.log2(1.0 / epsilon_pa)
    target = int(n * (1 - _h2(min(qber, 0.5))) - leaked_bits - pa_security)
    target = max(0, min(target, 256))   # SHA-256 ceiling
    if target == 0:
        return []

    key_str = "".join(str(b) for b in key)
    digest = hashlib.sha256(key_str.encode()).digest()
    out_bits = []
    for byte in digest:
        for shift in range(7, -1, -1):
            out_bits.append((byte >> shift) & 1)
            if len(out_bits) == target:
                return out_bits
    return out_bits


def bits_to_hex(bits):
    if not bits:
        return ""
    # pad to multiple of 4
    pad = (-len(bits)) % 4
    padded = bits + [0] * pad
    hex_str = ""
    for i in range(0, len(padded), 4):
        nibble = (padded[i] << 3) | (padded[i+1] << 2) | (padded[i+2] << 1) | padded[i+3]
        hex_str += f"{nibble:x}"
    return hex_str


def print_section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
