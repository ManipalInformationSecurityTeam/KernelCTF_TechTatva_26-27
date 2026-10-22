#!/usr/bin/env python3
"""Measure the WAV, recover its clock, decode, and export audio for inspection.

Uses only the WAV and memo conventions, without importing the generator.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import wave

import numpy as np
from solve import analytic_signal, bandpass_filter, bits_to_bytes, crc8_smbus, lfsr_descramble

PREAMBLE = [1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]


def write_audio(path, samples, fs):
    # Independent normalization affects playback level, not timing or frequency.
    gain = 0.95 / max(float(np.max(np.abs(samples))), 1e-12)
    pcm = np.rint(np.clip(samples * gain, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(pcm.tobytes())


def write_csv(path, header, rows):
    with path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def recover_frame(freq, fs, clock_anchor, period, coarse_start):
    # Test lattice boundaries around the energy onset; no flag length assumed.
    for ordinal in range(math.floor((coarse_start - .3 - clock_anchor) / period),
                         math.ceil((coarse_start + .3 - clock_anchor) / period) + 1):
        origin = clock_anchor + ordinal * period
        def symbols(count):
            edges = np.floor((origin + np.arange(count + 1) * period) * fs).astype(int)
            if edges[0] < 0 or edges[-1] >= len(freq):
                return []
            return [int(np.mean(freq[a:b]) > 1550) for a, b in zip(edges[:-1], edges[1:])]
        first = symbols(21)
        if first[:13] != PREAMBLE:
            continue
        length = bits_to_bytes(lfsr_descramble(first[13:]))[0]
        if not 1 <= length <= 255:
            continue
        count = 13 + 8 * (length + 2)
        full = symbols(count)
        if not full:
            continue
        decoded = bits_to_bytes(lfsr_descramble(full[13:]))
        payload = decoded[1:1 + length]
        crc = decoded[1 + length]
        if crc8_smbus(payload) == crc:
            try:
                flag = payload.decode('ascii')
            except UnicodeDecodeError:
                continue
            if flag.startswith('kernel{') and flag.endswith('}'):
                return origin, full, decoded, flag
    raise RuntimeError('No CRC-valid frame on the measured symbol grid')


def fit_carrier(times, frequencies, bits):
    # f = base + shift*bit + amplitude*sin(omega*t).
    # For each omega, the other three parameters are linear least squares.
    best = None
    def scan(omegas):
        nonlocal best
        for omega in omegas:
            design = np.column_stack((np.ones(len(times)), bits, np.sin(omega * times)))
            params = np.linalg.lstsq(design, frequencies, rcond=None)[0]
            mse = float(np.mean((design @ params - frequencies) ** 2))
            if best is None or mse < best[0]:
                best = mse, float(omega), params
    scan(np.linspace(.05, .5, 4501))
    scan(np.linspace(best[1] - .0001, best[1] + .0001, 201))
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('wav', type=Path)
    parser.add_argument('--out', type=Path, default=Path('analysis'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.wav), 'rb') as w:
        fs, channels, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        if channels != 2 or width != 2:
            raise ValueError('Expected stereo 16-bit PCM')
        audio = np.frombuffer(w.readframes(n), dtype='<i2').reshape(-1, 2).astype(float) / 32768
    side = (audio[:, 0] - audio[:, 1]) / 2
    filtered = bandpass_filter(side, 1100, 2000, fs)
    write_audio(args.out / 'side.wav', side, fs)
    write_audio(args.out / 'band.wav', filtered, fs)
    analytic = analytic_signal(filtered)
    frequency = np.angle(analytic[1:] * np.conj(analytic[:-1])) * fs / (2 * np.pi)
    frequency = np.pad(frequency, (0, 1), mode='edge')

    block = int(.02 * fs)
    energies = np.mean(filtered[:n // block * block].reshape(-1, block) ** 2, axis=1)
    active = np.flatnonzero(energies > .02 * np.max(energies))
    if len(active) == 0:
        raise RuntimeError('No transmission detected')
    start, end = active[0] * block / fs, (active[-1] + 1) * block / fs
    smooth = np.convolve(frequency, np.ones(96) / 96, mode='same')
    sliced = smooth > 1550
    crossings = np.flatnonzero(sliced[1:] != sliced[:-1]) + 1
    crossings = crossings[(crossings > (start + .25) * fs) & (crossings < (end - .25) * fs)]
    times = crossings / fs
    intervals = np.diff(times)
    single = intervals[(intervals > .020) & (intervals < .035)]
    initial_period = float(np.median(single))
    ordinals = np.concatenate(([0], np.cumsum(np.rint(intervals / initial_period)))).astype(int)
    period, clock_anchor = np.polyfit(ordinals, times, 1)
    origin, bits, decoded, flag = recover_frame(frequency, fs, clock_anchor, period, start)

    centers = origin + (np.arange(len(bits)) + .5) * period
    window_len, fft_len = 1024, 8192
    window = np.hanning(window_len)
    bins = np.fft.rfftfreq(fft_len, 1 / fs)
    candidate_bins = np.flatnonzero((bins >= 1100) & (bins <= 2000))
    peaks = []
    for center in centers:
        a = int(center * fs) - window_len // 2
        magnitude = np.abs(np.fft.rfft(side[a:a + window_len] * window, n=fft_len))
        j = candidate_bins[np.argmax(magnitude[candidate_bins])]
        logs = np.log(magnitude[j - 1:j + 2] + 1e-30)
        offset = .5 * (logs[0] - logs[2]) / (logs[0] - 2 * logs[1] + logs[2])
        peaks.append((j + offset) * fs / fft_len)
    peaks = np.array(peaks)
    relative_times = centers - origin
    keep = (relative_times > .25) & (relative_times < len(bits) * period - .25)
    mse, omega, params = fit_carrier(relative_times[keep], peaks[keep], np.array(bits)[keep])
    base, shift, amplitude = [float(x) for x in params]

    write_csv(args.out / 'transitions.csv', ['time_s', 'symbol_ordinal'], zip(times, ordinals))
    write_csv(args.out / 'symbols.csv', ['index', 'time_s', 'bit', 'peak_hz'],
              zip(range(len(bits)), centers, bits, peaks))
    write_csv(args.out / 'frequency_track.csv', ['time_s', 'frequency_hz'], zip(centers, peaks))
    write_csv(args.out / 'carrier_fit.csv', ['time_s', 'lower_tone_hz'],
              zip(centers, base + amplitude * np.sin(omega * relative_times)))
    mid = np.mean(audio, axis=1)
    mf, sf = np.fft.rfft(mid), np.fft.rfft(side)
    low = np.fft.rfftfreq(n, 1 / fs) < 300
    reduction = 10 * np.log10(np.sum(np.abs(mf[low]) ** 2) / np.sum(np.abs(sf[low]) ** 2))
    report = {
        'input_sha256': hashlib.sha256(args.wav.read_bytes()).hexdigest(),
        'python': platform.python_version(), 'numpy': np.__version__,
        'sample_rate_hz': fs, 'channels': channels, 'sample_width_bytes': width,
        'duration_s': n / fs, 'energy_window_start_s': start, 'energy_window_end_s': end,
        'frame_start_s': float(origin), 'baud': float(1 / period),
        'symbol_duration_ms': float(period * 1000), 'samples_per_symbol': float(period * fs),
        'preamble': ''.join(map(str, bits[:13])), 'payload_bytes': decoded[0],
        'whitened_bytes': len(decoded), 'total_symbols': len(bits),
        'burst_duration_s': float(len(bits) * period), 'frame_end_s': float(origin + len(bits) * period),
        'base_frequency_hz': base, 'tone_spacing_hz': shift, 'drift_amplitude_hz': amplitude,
        'angular_frequency_rad_s': omega, 'drift_rate_hz': float(omega / (2 * np.pi)),
        'drift_period_s': float(2 * np.pi / omega), 'frequency_fit_rmse_hz': float(np.sqrt(mse)),
        'sub_300_hz_mid_to_side_reduction_db': float(reduction),
        'decoded_frame_hex': decoded.hex(' '), 'received_crc_hex': f'{decoded[-1]:02x}',
        'calculated_crc_hex': f'{crc8_smbus(decoded[1:-1]):02x}', 'flag': flag,
    }
    (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
