#!/usr/bin/env python3
"""
solve.py  --  PLAYER SIDE: the full intended path, step by step.

 1. LSBs of the PNGs        -> 2x2 Hill matrix + 4 encrypted letters
 2. Hill-decrypt the letters -> which image is HEAD / TAIL
 3. image 1 ticks -> bits -> 5-bit groups -> Baudot
 4. image 2 ticks -> bits -> 5-bit groups -> reverse EACH group -> Baudot
 5. join the halves in the order the Hill message gave

Usage:
    python solve.py image1.png image2.png
"""
import sys
from extract_lsb import extract_lsb_bytes, parse_payload
from decode_image1 import read_bits, to_groups, baudot_decode


def mod_inverse_matrix(k):
    det = (k[0][0] * k[1][1] - k[0][1] * k[1][0]) % 26
    inv_det = pow(det, -1, 26)                      # raises if not invertible
    return [[(k[1][1] * inv_det) % 26, (-k[0][1] * inv_det) % 26],
            [(-k[1][0] * inv_det) % 26, (k[0][0] * inv_det) % 26]]


def hill_decrypt(cipher_vals, key):
    inv = mod_inverse_matrix(key)
    out = []
    for i in range(0, len(cipher_vals), 2):
        a, b = cipher_vals[i], cipher_vals[i + 1]
        out.append((inv[0][0] * a + inv[0][1] * b) % 26)
        out.append((inv[1][0] * a + inv[1][1] * b) % 26)
    return "".join(chr(65 + v) for v in out)


def _args():
    return [a for a in sys.argv[1:] if not a.startswith("-")]


if __name__ == "__main__":
    a = _args()
    p1 = a[0] if len(a) > 0 else "image1.png"
    p2 = a[1] if len(a) > 1 else "image2.png"
    parts = {}
    for name, path, reverse in (("image1", p1, False), ("image2", p2, True)):
        key, cipher = parse_payload(extract_lsb_bytes(path, 8))
        role = hill_decrypt(cipher, key)
        groups = to_groups(read_bits(path))
        if reverse:
            groups = [list(reversed(g)) for g in groups]
        text = baudot_decode(groups)
        print("%s: LSB matrix=%s  hill message=%s  visual text=%s" % (name, key, role, text))
        parts[role] = text
    flag = parts["HEAD"] + parts["TAIL"]
    print("flag:", flag)
