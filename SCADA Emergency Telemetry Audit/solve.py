#!/usr/bin/env python3
"""
SCADA EMERGENCY — Reference Solver
Demodulates and recovers the emergency telemetry packet from scada_emergency_capture.wav:
  1. Computes stereo side channel: S(t) = (L(t) - R(t)) / 2
  2. Applies bandpass filter (1100 Hz - 2000 Hz) via pure NumPy FFT
  3. Computes instantaneous frequency using pure NumPy analytic signal (FM discriminator)
  4. Detects transmission burst and performs frame synchronization using bipolar Barker-13
  5. Slices non-integer baud rate symbols (N_sym = 9000/7 samples/symbol)
  6. Descrambles payload using 7-bit LFSR (x^7 + x^4 + 1, seed 0x7F)
  7. Validates packet length and CRC-8/SMBUS
  8. Prints the recovered flag: kernel{...}
"""

import math
import os
import sys
import wave
import numpy as np

# Barker-13 bipolar sequence (+1 for bit 1, -1 for bit 0)
BARKER_13_BIPOLAR = np.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=np.float64)


def crc8_smbus(data: bytes) -> int:
    """Computes CRC-8/SMBUS (Poly: 0x07, Init: 0x00, Final XOR: 0x00)."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def lfsr_descramble(bits: list, seed: int = 0x7F) -> list:
    """Additive 7-bit LFSR descrambler (G(x) = x^7 + x^4 + 1, seed 0x7F)."""
    state = seed & 0x7F
    descrambled = []
    for b in bits:
        feedback = ((state >> 6) ^ (state >> 3)) & 1
        descrambled.append(b ^ feedback)
        state = ((state << 1) | feedback) & 0x7F
    return descrambled


def bits_to_bytes(bits: list) -> bytes:
    """Converts a bit list (MSB-first) to bytes."""
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        chunk = bits[i:i + 8]
        for bit in chunk:
            byte_val = (byte_val << 1) | bit
        if len(chunk) < 8:
            byte_val <<= (8 - len(chunk))
        out.append(byte_val)
    return bytes(out)


def analytic_signal(x: np.ndarray) -> np.ndarray:
    """Computes the analytic signal z[n] = x[n] + j*H{x[n]} using pure NumPy FFT."""
    N = len(x)
    X = np.fft.fft(x)
    h = np.zeros(N)
    if N % 2 == 0:
        h[0] = 1.0
        h[N // 2] = 1.0
        h[1 : N // 2] = 2.0
    else:
        h[0] = 1.0
        h[1 : (N + 1) // 2] = 2.0
    return np.fft.ifft(X * h)


def bandpass_filter(x: np.ndarray, f_low: float, f_high: float, fs: int) -> np.ndarray:
    """Raised-cosine frequency-domain bandpass filter."""
    N = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(N, d=1.0 / fs)

    H = np.zeros_like(freqs)
    pass_mask = (freqs >= f_low) & (freqs <= f_high)
    H[pass_mask] = 1.0

    trans = 75.0
    low_skirt = (freqs >= (f_low - trans)) & (freqs < f_low)
    H[low_skirt] = 0.5 * (1.0 + np.cos(np.pi * (f_low - freqs[low_skirt]) / trans))

    high_skirt = (freqs > f_high) & (freqs <= (f_high + trans))
    H[high_skirt] = 0.5 * (1.0 + np.cos(np.pi * (freqs[high_skirt] - f_high) / trans))

    return np.fft.irfft(X * H, n=N)


def solve(wav_path: str) -> str:
    print(f"[-] Loading audio file: {wav_path}")
    if not os.path.exists(wav_path):
        print(f"[!] File not found: {wav_path}")
        sys.exit(1)

    with wave.open(wav_path, "rb") as wf:
        fs = wf.getframerate()
        n_ch = wf.getnchannels()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    if n_ch != 2:
        print(f"[!] Expected stereo WAV, got {n_ch} channels")
        sys.exit(1)

    print(f"    Sample rate: {fs} Hz | Channels: {n_ch} | Duration: {n_frames / fs:.1f}s")
    audio = np.frombuffer(raw_bytes, dtype=np.int16).reshape(-1, 2)
    left = audio[:, 0].astype(np.float64) / 32768.0
    right = audio[:, 1].astype(np.float64) / 32768.0

    # Step 1: Channel Subtraction (Mid/Side Side Channel)
    print("[-] Step 1: Computing Mid/Side Side channel S(t) = (L - R) / 2...")
    S = (left - right) / 2.0

    # Step 2: Bandpass filter 1100 Hz - 2000 Hz
    print("[-] Step 2: Applying bandpass filter (1100 Hz - 2000 Hz)...")
    S_bp = bandpass_filter(S, 1100.0, 2000.0, fs)

    # Step 3: Pure NumPy Analytic Signal & FM Discriminator
    print("[-] Step 3: Computing instantaneous frequency via FM discriminator...")
    z = analytic_signal(S_bp)
    v_disc = np.angle(z[1:] * np.conj(z[:-1])) * (fs / (2.0 * np.pi))
    v_disc = np.pad(v_disc, (0, 1), mode="edge")

    # Step 4: Clock & Burst Detection
    R_sym = 112.0 / 3.0  # 37.3333... Baud
    N_sym = fs / R_sym   # 9000/7 ~ 1285.714 samples/symbol
    print(f"[-] Step 4: Symbol clock grid: {R_sym:.2f} Baud ({N_sym:.3f} samples/symbol)...")

    # Locate transmission burst by energy
    block_len = int(0.5 * fs)
    energies = [np.mean(S_bp[i:i + block_len] ** 2) for i in range(0, len(S_bp) - block_len, block_len)]
    threshold = np.median(energies) * 3.0
    active_blocks = [i for i, e in enumerate(energies) if e > threshold]

    if not active_blocks:
        search_start = 0
        search_end = len(S_bp)
    else:
        search_start = max(0, int((active_blocks[0] * 0.5 - 0.5) * fs))
        search_end = min(len(S_bp), int((active_blocks[-1] * 0.5 + 0.5) * fs))

    print(f"    Scanning burst window: {search_start / fs:.2f}s to {search_end / fs:.2f}s")

    # Step 5: Frame Synchronization & Demodulation
    step = int(N_sym / 8)  # Sample search resolution
    recovered_flag = None

    for n0 in range(search_start, search_end, step):
        # Test candidate Barker-13 sequence
        bits_test = []
        for k in range(13):
            s_idx = n0 + int(math.floor(k * N_sym))
            e_idx = n0 + int(math.floor((k + 1) * N_sym))
            if e_idx >= len(v_disc):
                break
            mean_f = np.mean(v_disc[s_idx:e_idx])
            bits_test.append(1.0 if mean_f > 1550.0 else -1.0)

        if len(bits_test) < 13:
            continue

        score = np.dot(bits_test, BARKER_13_BIPOLAR)
        if score >= 12.0:
            # Preamble match! Slicing 400 symbols from lock point
            symbols = []
            for k in range(400):
                s_idx = n0 + int(math.floor(k * N_sym))
                e_idx = n0 + int(math.floor((k + 1) * N_sym))
                if e_idx >= len(v_disc):
                    break
                mean_f = np.mean(v_disc[s_idx:e_idx])
                symbols.append(1 if mean_f > 1550.0 else 0)

            # Extract payload bits (after 13 Barker bits)
            payload_bits = symbols[13:]
            descrambled_bits = lfsr_descramble(payload_bits, seed=0x7F)
            raw_bytes = bits_to_bytes(descrambled_bits)

            if len(raw_bytes) >= 3:
                length = raw_bytes[0]
                expected_total = 1 + length + 1
                if len(raw_bytes) >= expected_total:
                    flag_bytes = raw_bytes[1:1 + length]
                    rx_crc = raw_bytes[1 + length]
                    calc_crc = crc8_smbus(flag_bytes)

                    if calc_crc == rx_crc:
                        try:
                            candidate_flag = flag_bytes.decode("ascii")
                            if candidate_flag.startswith("kernel{") and candidate_flag.endswith("}"):
                                print(f"[+] Frame lock at sample {n0} (t = {n0 / fs:.3f}s | Barker score = {score:.1f})")
                                print(f"[+] CRC-8/SMBUS check: VALID (0x{calc_crc:02X})")
                                recovered_flag = candidate_flag
                                break
                        except Exception:
                            pass

    if recovered_flag:
        print("\n" + "=" * 50)
        print(f"[+] FLAG: {recovered_flag}")
        print("=" * 50)
        return recovered_flag
    else:
        print("[!] Failed to recover flag.")
        sys.exit(1)


if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_wav = os.path.join(project_dir, "release", "scada_emergency_capture.wav")
    target_wav = sys.argv[1] if len(sys.argv) > 1 else default_wav
    solve(target_wav)
