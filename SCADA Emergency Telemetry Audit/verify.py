#!/usr/bin/env python3
"""Check a reproduced analysis against the current challenge artifact."""
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else 'analysis/report.json').read_text())
expected = {
    'input_sha256': '75c42526e60826837091d59982bdb98e408e9e645e60d23e565b7c9fcdb7d284',
    'flag': 'kernel{s0undw4v3s?_d1dn7_kn0w_7h3y_h4v3_h4nd5}',
    'preamble': '1111100110101', 'payload_bytes': 46, 'whitened_bytes': 48,
    'total_symbols': 397, 'received_crc_hex': '55', 'calculated_crc_hex': '55',
}
for key, value in expected.items():
    if report[key] != value:
        raise SystemExit(f'FAIL {key}: {report[key]!r}; expected {value!r}')
for key, target, tolerance in [
    ('frame_start_s', 18.5, .0001), ('frame_end_s', 29.13394, .0001),
    ('baud', 112 / 3, .0001), ('base_frequency_hz', 1350, .02),
    ('tone_spacing_hz', 400, .02), ('drift_amplitude_hz', 65, .02),
    ('angular_frequency_rad_s', .219911, .00001),
]:
    if abs(report[key] - target) > tolerance:
        raise SystemExit(f'FAIL {key}: {report[key]}; expected {target} +/- {tolerance}')
print('PASS: input hash, measured parameters, packet length, preamble, CRC, and flag match.')
