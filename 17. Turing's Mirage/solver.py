#!/usr/bin/env python3
"""
solver.py
Reference Solution for "Turing's Mirage" (Hardened Anti-AI Edition).

Dual-Phase Solution:
1. Phase 1 (Reverse Engineering / Container Forensics):
   - Reads challenge.cng
   - Strips the AI prompt injection honeypot tEXt chunk
   - Recalculates standard CRC32 (reversing the 0xDEADBEEF XOR key found in `viewer`)
   - Reconstructs solved.png
2. Phase 2 (Steganography / Spatial Matrix Reconstruction):
   - Decomposes solved.png into Red, Green, Blue, Alpha channels
   - Samples 20x20 cell centers to extract 15x15 binary matrices
   - Deductively identifies quadrants using QR 7x7 Finder Pattern signatures
   - Reassembles the full QR matrix and scans the real flag
"""

import struct
import zlib
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image

CNG_MAGIC = b"\x89CNG\r\n\x1a\n"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
XOR_KEY = 0xDEADBEEF

BASE_DIR = Path(__file__).resolve().parent
CNG_PATH = BASE_DIR / "challenge" / "challenge.cng"
if not CNG_PATH.exists():
    CNG_PATH = BASE_DIR / "challenge.cng"
SOLVED_PNG_PATH = BASE_DIR / "solved.png"
RECONSTRUCTED_QR_PATH = BASE_DIR / "reconstructed_qr.png"

MODULE_SCALE = 20
QUADRANT_DIM = 15


def phase1_reconstruct_container(input_cng=CNG_PATH, output_png=SOLVED_PNG_PATH):
    print("=" * 65)
    print("[*] Phase 1: Reconstructing PNG from CNG container...")
    print("=" * 65)
    raw = Path(input_cng).read_bytes()
    assert raw.startswith(CNG_MAGIC), "Not a valid CNG file!"
    print(f"[+] Verified CNG Magic Header (89 43 4E 47 0D 0A 1A 0A)")

    offset = 8
    clean_chunks = []

    while offset < len(raw):
        length = struct.unpack(">I", raw[offset:offset+4])[0]
        chunk_type = raw[offset+4:offset+8]
        chunk_data = raw[offset+8:offset+8+length]
        stored_crc = struct.unpack(">I", raw[offset+8+length:offset+12+length])[0]

        # 1. Skip the AI Prompt Injection decoy chunk
        if chunk_type == b"tEXt" and b"System Override" in chunk_data:
            print("[!] AI Prompt Injection Honeypot detected in tEXt chunk -> Discarding decoy.")
            offset += 12 + length
            continue

        # 2. Recalculate true IEEE 802.3 CRC32
        computed_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF

        # 3. Verify and reverse 0xDEADBEEF XOR for critical chunks
        if chunk_type in [b"IHDR", b"IDAT"]:
            assert (stored_crc ^ XOR_KEY) == computed_crc, f"CRC mismatch on {chunk_type}"
            print(f"[+] Successfully reversed XOR key 0xDEADBEEF for {chunk_type.decode()} chunk")

        clean_chunks.append((chunk_type, chunk_data, computed_crc))
        offset += 12 + length

    # 4. Serialize to standard PNG
    with open(output_png, "wb") as f:
        f.write(PNG_MAGIC)
        for c_type, c_data, c_crc in clean_chunks:
            f.write(struct.pack(">I", len(c_data)))
            f.write(c_type)
            f.write(c_data)
            f.write(struct.pack(">I", c_crc))

    print(f"[+] Reconstructed image container written to: {output_png.name}")
    with Image.open(output_png) as img:
        img.verify()
    print("[✓] PNG container verification successful!\n")
    return output_png


def phase2_reconstruct_matrix(solved_png=SOLVED_PNG_PATH, output_qr=RECONSTRUCTED_QR_PATH):
    print("=" * 65)
    print("[*] Phase 2: Resolving RGBA Chroma Matrix & QR Puzzle...")
    print("=" * 65)
    img = Image.open(solved_png)
    assert img.mode == "RGBA", f"Expected RGBA image, got {img.mode}"
    print(f"[+] Loaded {img.size[0]}x{img.size[1]} image with {img.mode} channels")

    r, g, b, a = img.split()
    channel_dict = {
        "Red": np.array(r),
        "Green": np.array(g),
        "Blue": np.array(b),
        "Alpha": np.array(a),
    }

    half = MODULE_SCALE // 2
    matrices = {}
    for name, ch in channel_dict.items():
        grid = np.zeros((QUADRANT_DIM, QUADRANT_DIM), dtype=np.uint8)
        for y in range(QUADRANT_DIM):
            for x in range(QUADRANT_DIM):
                val = ch[y * MODULE_SCALE + half, x * MODULE_SCALE + half]
                grid[y, x] = 1 if val > 128 else 0
        matrices[name] = grid
        print(f"[+] Channel {name:5s}: Extracted {QUADRANT_DIM}x{QUADRANT_DIM} matrix (Black modules: {grid.sum()})")

    # Deduce Quadrants using 7x7 Finder Pattern landmark signatures (33 black modules)
    quadrants = {}
    assigned_channels = {}

    for name, mat in matrices.items():
        tl_sum = mat[0:7, 0:7].sum()
        tr_sum = mat[0:7, 7:14].sum()
        bl_sum = mat[7:14, 0:7].sum()

        if tl_sum == 33:
            quadrants["TL"] = mat
            assigned_channels["TL"] = name
        elif tr_sum == 33:
            quadrants["TR"] = mat
            assigned_channels["TR"] = name
        elif bl_sum == 33:
            quadrants["BL"] = mat
            assigned_channels["BL"] = name
        else:
            quadrants["BR"] = mat
            assigned_channels["BR"] = name

    print("\n[*] Deductive Quadrant Mapping (Based on QR Anatomical Landmarks):")
    for q_name in ["TL", "TR", "BL", "BR"]:
        print(f"    - Quadrant {q_name}: Sourced from {assigned_channels.get(q_name, 'Unknown')} Channel")

    top_row = np.hstack([quadrants["TL"], quadrants["TR"]])
    bot_row = np.hstack([quadrants["BL"], quadrants["BR"]])
    full_30 = np.vstack([top_row, bot_row])

    # Crop to 29x29 and add 2 modules quiet zone border
    qr_with_border = np.pad(full_30[:29, :29], 2, mode="constant", constant_values=0)
    scale = 10
    qr_pixels = ((1 - np.repeat(np.repeat(qr_with_border, scale, axis=0), scale, axis=1)) * 255).astype(np.uint8)
    qr_img = Image.fromarray(qr_pixels, mode="L")
    qr_img.save(output_qr)
    print(f"\n[+] Rendered full QR code to: {output_qr.name}")

    # Decode flag with zbarimg
    flag = None
    try:
        res = subprocess.run(["zbarimg", "--raw", "-q", str(output_qr)], capture_output=True, text=True, check=True)
        flag = res.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            from pyzbar.pyzbar import decode
            decoded = decode(qr_img)
            if decoded:
                flag = decoded[0].data.decode("utf-8")
        except ImportError:
            pass

    if flag:
        print("=" * 65)
        print(f"[★] RECOVERED TRUE FLAG: {flag}")
        print("=" * 65)
        return flag
    else:
        print("[!] Reconstructed QR code saved. Please scan with phone or zbarimg.")
        return None


def solve():
    phase1_reconstruct_container()
    return phase2_reconstruct_matrix()


if __name__ == "__main__":
    solve()
