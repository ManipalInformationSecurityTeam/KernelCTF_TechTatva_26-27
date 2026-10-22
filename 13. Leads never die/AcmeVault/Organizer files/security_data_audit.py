#!/usr/bin/env python3
"""Static sanity checks for the public/private case-data boundary."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text()
CLIENT = "\n".join((p.read_text() for p in (ROOT / "templates").glob("*.html"))) + "\n" + (ROOT / "static" / "style.css").read_text()

forbidden_in_client = [
    "PRIVATE_CASE_DATA",
    "RESTRICTED_FLAG",
    "kernel{",
    "ARCHIVE GATEWAY / TECHNICAL ADDENDUM",
    "SECURITY OPERATIONS / ADDENDUM",
    "RESEARCH NOTEBOOK / ADDENDUM",
    "Pythons get scrambled",
]
leaks = [value for value in forbidden_in_client if value in CLIENT]
assert not leaks, f"Private content referenced by client assets: {leaks}"

assert "PRIVATE_CASE_DATA" in APP
assert "SEALED_ADDENDUM_CASES" in APP
assert 'render_case["addendum"] = dict(PRIVATE_CASE_DATA[case_id])' in APP
assert 'render_case["flag"] = RESTRICTED_FLAG' in APP
assert 'cases=public_cards' in APP
assert '"has_addendum"' not in APP
assert '"sealed_count"' not in APP

suspects = (ROOT / "templates" / "suspects.html").read_text()
case = (ROOT / "templates" / "case.html").read_text()
assert "has_addendum" not in suspects
assert "SEALED EVIDENCE ADDENDUM" not in case
assert "ACCESS RESTRICTED" not in case

print("SECURITY DATA BOUNDARY: PASS")
print("- sealed addenda are server-side only")
print("- flag is server-side only")
print("- suspect cards expose no addendum marker")
print("- case pages expose no locked-addendum placeholder")
