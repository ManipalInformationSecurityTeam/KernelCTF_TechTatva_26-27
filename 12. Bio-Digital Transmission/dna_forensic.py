import numpy as np
from scipy.io import wavfile
import struct
import json

# ============================================================
# 1. GENERATE AUDIO (Octave Spacing for Audacity Log Scale)
# ============================================================

# Translates to "EXON" using A=00, G=01, T=10, C=11
DNA_SEQUENCE = "GAGGGGTAGACCGACT"

# Octave spacing (each is 2x the last). 
# Looks evenly spaced and identically thick on Audacity's default Logarithmic scale.
FREQ_MAP = {
    'A': 1000, 
    'G': 2000, 
    'T': 4000, 
    'C': 8000  
}

sr = 44100
segment_duration = 0.8
segment_samples = int(sr * segment_duration)
total_samples = len(DNA_SEQUENCE) * segment_samples

print(f"[*] DNA: {DNA_SEQUENCE}")
print(f"[*] Frequencies: A=1kHz, G=2kHz, T=4kHz, C=8kHz")
print(f"[*] Total time: {total_samples/sr:.1f}s\n")

audio = np.zeros(total_samples)

for i, base in enumerate(DNA_SEQUENCE):
    freq = FREQ_MAP[base]
    start = i * segment_samples
    end = start + segment_samples
    
    t = np.arange(segment_samples) / sr
    tone = 0.95 * np.sin(2 * np.pi * freq * t)
    
    # Smooth fade in
    fade = int(0.06 * sr)
    tone[:fade] *= np.linspace(0, 1, fade)
    
    # 0.2-second silent gap so repeated bases don't bleed together visually
    gap_samples = int(sr * 0.2)
    tone[-(gap_samples + fade):-gap_samples] *= np.linspace(1, 0, fade)
    tone[-gap_samples:] = 0 
    
    audio[start:end] = tone

audio = audio / np.max(np.abs(audio)) * 0.98
wavfile.write("challenge.wav", sr, np.int16(audio * 32767))

# ============================================================
# 2. DERIVE KEY FROM SEQUENCE
# ============================================================

def dna_to_key(sequence):
    base_map = {'A': '00', 'G': '01', 'T': '10', 'C': '11'}
    binary = "".join(base_map[b] for b in sequence)
    return "".join(chr(int(binary[i:i+8], 2)) for i in range(0, len(binary), 8))

key = dna_to_key(DNA_SEQUENCE)
print(f"[*] Derived Key: {key}")

# ============================================================
# 3. VIGENERE ENCRYPTION
# ============================================================

# The final CTF flag replacing the coordinates
json_str = json.dumps({" ": "unz1pp1ng_my_g3n3s"})

def vigenere_encrypt(text, key):
    key = key.upper()
    cipher = ""
    key_idx = 0
    for char in text:
        if char.isalpha():
            shift = ord(key[key_idx % len(key)]) - 65
            if char.islower():
                cipher += chr((ord(char) - 97 + shift) % 26 + 97)
            else:
                cipher += chr((ord(char) - 65 + shift) % 26 + 65)
            key_idx += 1
        else:
            cipher += char # Preserve numbers, brackets, and symbols
    return cipher

encrypted_payload = vigenere_encrypt(json_str, key)
print(f"[*] Plaintext: {json_str}")
print(f"[*] Vigenere:  {encrypted_payload}\n")

# ============================================================
# 4. INJECT EXIFTOOL-COMPLIANT METADATA
# ============================================================

with open("challenge.wav", 'r+b') as f:
    data = bytearray(f.read())
    
    # Prepare standard ICMT (Comment) tag data
    payload_bytes = encrypted_payload.encode('utf-8') + b'\x00'
    
    # Add padding byte if chunk size is odd (WAV format requirement)
    pad = len(payload_bytes) % 2
    payload_bytes += b'\x00' * pad
    
    # Build RIFF LIST/INFO/ICMT chunk
    icmt_chunk = b'ICMT' + struct.pack('<I', len(payload_bytes)) + payload_bytes
    list_payload = b'INFO' + icmt_chunk
    list_chunk = b'LIST' + struct.pack('<I', len(list_payload)) + list_payload
    
    # Append to file and update master file size in the RIFF header
    data.extend(list_chunk)
    data[4:8] = struct.pack('<I', len(data) - 8)
    
    f.seek(0)
    f.write(data)

print(f"[+] Clean metadata injected (ICMT comment tag).")
print(f"[+] CHALLENGE READY!")