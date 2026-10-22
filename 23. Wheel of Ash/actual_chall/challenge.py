from Crypto.PublicKey import RSA
from Crypto.Util.number import bytes_to_long, long_to_bytes

# --- RSA key generation ---
_key = RSA.generate(2048)
n = _key.n
e = _key.e
d = _key.d

# --- the flag, fixed ---
FLAG = b"kernel{n3v3r_7ru57_7h3_0bvi0u5}"

M1 = bytes_to_long(FLAG)

# sanity check: RSA math only works correctly if M1 < n
assert M1 < n, "FLAG is too large for this RSA modulus! Generate a bigger key."

# --- the Measure ---
R = 12345  # arbitrary, fixed, known to the player

# --- compute the Echo ---
M2 = (M1 + R) % n
Echo = pow(M2, e, n)

def oracle(Cx):
    """
    Given a ciphertext Cx, decrypt it, compare the result to the
    hidden M2, and return True or False.
    This is the only way anything outside this file ever touches
    d or M2 -- through this one function's return value.
    """
    x = pow(Cx, d, n)

    delta = (x - M2) % n

    if delta > (n - 1) // 2:
        delta -= n

    return delta > 0

if __name__ == "__main__":
    print("n     =", n)
    print("e     =", e)
    print("R     =", R)
    print("Echo  =", Echo)
    print()
    print("--- secrets (for our eyes only, sanity-checking) ---")
    print("M1    =", M1)
    print("M2    =", M2)
    print("d     =", d)
    print("M1 < n ?", M1 < n)
