# SCADA Emergency Telemetry Audit

## Author
yam1_

## Domain
Forensics

## Difficulty
Medium

## Challenge Description

An emergency telemetry packet is hidden in the ambient sound of a pipeline monitoring station. Analyze the stereo capture and vendor protocol memo to recover the transmitted payload and submit the flag.

## Intended Solution

The emergency SCADA traffic is a binary frequency-shift keyed packet mixed into a stereo acoustic monitoring recording. Subtracting the channels suppresses the facility drone, exposing two tones. Recovering the symbol clock, removing the LFSR whitener, and checking CRC-8/SMBus yields:  

This solution applies to the regenerated WAV containing the 46-byte flag above. Its burst is approximately 18.500–29.134 seconds. Older screenshots showing an end near 27.85 seconds belong to the previous payload.

### Tools and files

| Tool | Version checked | Role |
|---|---|---|
| Python | 3.14.7 | Executed the measurement and decoding scripts |
| NumPy | 2.5.3 | FFT filtering, analytic signal, spectral peaks, and least squares |
| Python standard library | Included with Python | WAV reading and writing, CSV, JSON, and SHA-256 |
| Sonic Visualiser | 5.2.1 | Optional visual inspection using the settings below; its installed version was checked, while the numerical results were obtained with Python |

The project includes `solution/analyze.py`, `solution/solve.py`, `solution/verify.py`, and expected output files. `solution/analyze.py` imports DSP and codec helpers from `solution/solve.py`, so keep both scripts in the same directory. It does not import the challenge generator or its constants. The reference solver's default path now points to the renamed capture in this project.

The input WAV and vendor memo are in the project `release` directory. Run the commands below from the project root; the scripts can also take an absolute WAV path.

**Reproduce the result:**  
Use Python 3 with NumPy. The tested versions were Python 3.14.7 and NumPy 2.5.3. To create a separate environment from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Confirm the input, run the analysis and the reference solver, then check the measured results:

```bash
sha256sum release/scada_emergency_capture.wav
python3 solution/analyze.py release/scada_emergency_capture.wav --out solution/analysis
python3 solution/solve.py release/scada_emergency_capture.wav
python3 solution/verify.py solution/analysis/report.json
```

The SHA-256 must be:

```text
75c42526e60826837091d59982bdb98e408e9e645e60d23e565b7c9fcdb7d284
```

Expected final verification output:

```text
PASS: input hash, measured parameters, packet length, preamble, CRC, and flag match.
```

`solution/expected_report.json` records the full tested measurements. `solution/expected_analysis_output.txt` and `solution/expected_solver_output.txt` record the scripts' output. Version strings and the final few floating-point digits can differ on another Python or NumPy build; `solution/verify.py` compares the decisive fields exactly and numerical estimates within small tolerances.

The source recording is 48,000 Hz, two-channel, 16-bit PCM, and exactly 75 seconds long. The analyzer exports:

| Output | Purpose |
|---|---|
| `solution/analysis/side.wav` | Mono difference channel, with its original 75-second timeline |
| `solution/analysis/band.wav` | Difference channel filtered around the telemetry band |
| `solution/analysis/transitions.csv` | Detected tone-change times and fitted symbol ordinals |
| `solution/analysis/symbols.csv` | Each recovered symbol, centre time, and measured tone frequency |
| `solution/analysis/frequency_track.csv` | Time and measured frequency, suitable for inspection |
| `solution/analysis/carrier_fit.csv` | Fitted lower-tone trajectory |
| `solution/analysis/report.json` | Parameters, decoded bytes, CRC, and flag |

Both exported WAVs are independently normalized to 95% peak for convenient viewing and listening. Their amplitudes therefore differ from the source; their timing and frequency content are preserved. The reported drone reduction is measured on the original floating-point signals before this normalization.

**Inspect the transmission in Sonic Visualiser:**  
Open `solution/analysis/band.wav` with File → Open. Add a spectrogram from the Pane menu. In its properties, apply the settings below; choose Hann in application preferences. Use Navigate and Shift-drag to zoom to the burst. The [official Sonic Visualiser reference](https://www.sonicvisualiser.org/doc/reference/5.2.1/en/) describes these controls and the time–frequency resolution tradeoff.

| Setting | Value for this recording |
|---|---|
| Window size | 1024 samples |
| Window shape | Hann |
| Window overlap | 75% |
| Oversampling | 8× |
| Frequency scale | Linear |
| Frequency view | Approximately 1100–2000 Hz |
| Time view for the whole burst | Approximately 18–30 seconds |
| Time view for the preamble | Approximately 18.48–18.87 seconds |
| Colour scale | dBV; adjust display gain for visibility |
| Normalization | Off for comparing levels across time |

Keep Bin Display on its ordinary bin view to inspect symbol boundaries. Switch it to Frequencies, or add a Peak Frequency Spectrogram with the same window settings, for tone readings. Use the Measure tool for times and frequencies. Save the layout with File → Save Session As if you want to reopen it later. These viewing controls are described in the [spectrogram section of the reference](https://www.sonicvisualiser.org/doc/reference/5.2.1/en/).

A 1024-sample window lasts 21.333 ms, shorter than the 26.786 ms symbol duration. A 4096-sample window lasts 85.333 ms and blends several short symbols. The 75% overlap gives a 256-sample, 5.333 ms display hop. Oversampling smooths the frequency display; it does not replace a longer observation window.

Expect a lower track near 1350–1415 Hz and an upper track near 1750–1815 Hz. Both move together. The gap is approximately 400 Hz. During the first 13 symbol intervals, count five high symbols, two low, two high, one low, one high, one low, and one high:

```text
1111100110101
```

Runs of equal bits form one longer tone segment. The first high segment contains five symbols, so measuring that entire segment as a single symbol would produce the wrong baud rate. Measure several short transitions, or use the clock fit below. The 200 ms fade at burst onset makes the first symbols dimmer; display gain may need adjustment.

The GUI is for inspection and approximate measurements. The exported report gives the reproducible numerical estimates. A static magnitude spectrogram alone does not establish phase continuity, and the partial drift cycle does not provide a directly measurable full period.

**Isolate the difference channel and demodulate:**  
The memo describes opposite polarity across the two transmit feeds. Convert the PCM samples to floating point before subtracting, avoiding signed 16-bit overflow:

```python
audio = pcm.astype(float) / 32768.0
side = (audio[:, 0] - audio[:, 1]) / 2.0
```

The common drone mostly cancels. The analyzer measures approximately 25.937 dB of reduction in energy below 300 Hz, comparing the mid channel `(L + R) / 2` with the side channel. Raw left and right samples are not consistently opposite in sign because both also contain the common ambience.

The filter retains 1100–2000 Hz and uses 75 Hz raised-cosine transition skirts. It runs an FFT over the whole recording, multiplies by this frequency response, and transforms back. This removes the remaining low-frequency ambience without requiring SciPy or an audio plugin.

Construct an analytic signal by retaining DC and Nyquist, doubling the positive FFT frequencies, and setting the negative frequencies to zero. The phase increment gives instantaneous frequency:

$$
f[n] = \frac{F_s}{2\pi}\arg\left(z[n]\overline{z[n-1]}\right).
$$

Bits are distinguished by which tone the frequency estimate occupies. A 1550 Hz threshold lies between the observed tracks. The carrier drift does not make the bands overlap in this recording, so a moving threshold is unnecessary.

**Recover timing from the recording:**  
The analyzer computes energy in 20 ms blocks and marks blocks exceeding 2% of the maximum filtered energy. This gives an approximate active interval of 18.54–29.08 seconds. The fade means those energy edges lie inside the transmitted packet; they are not its exact framing boundaries.

Smooth the frequency discriminator over 96 samples, or 2 ms, and locate crossings of 1550 Hz. Keep crossings at least 250 ms inside each energy boundary to exclude the fades. Take the median spacing of crossings separated by 20–35 ms as the first estimate of a single symbol period.

Consecutive crossings can be several symbols apart. Round each interval divided by the initial period to an integer, accumulate these integers into symbol ordinals, and fit:

$$
t_i = a + k_i T_s.
$$

This produces approximately:

```text
baud                  37.33333837 symbols/s
symbol duration       26.78571067 ms
samples per symbol    1285.71411223
```

This timing comes from the recording rather than a hard-coded `112/3` baud rate. The reference solver separately uses the rational rate `112/3`, which agrees with the measurement.

Test boundaries on the fitted clock lattice within 300 ms of the approximate energy onset. Sample 13 preamble symbols and the next eight bits. A Barker match identifies a candidate frame; descrambling the next byte gives its payload length. Read exactly the number of symbols implied by that length, then validate the CRC and ASCII flag format.

Use fractional boundaries `floor((origin + k * period) * fs)` for every symbol. Repeatedly adding 1285 or 1286 samples accumulates timing error.

The independently measured frame starts at approximately 18.49999817 seconds and ends at 29.13392531 seconds. The reference solver reports a slightly earlier lock at 18.493 seconds because it searches a coarse grid of candidate offsets and accepts the first CRC-valid decode. That is a valid decode offset, rather than a precision onset measurement.

**Measure the frequency model:**  
The memo supplies the model and defines time from burst onset:

$$
f_0(t) = f_{\mathrm{base}} + \Delta f_{\mathrm{drift}}\sin(\omega_d t),
\qquad
f_1(t) = f_0(t) + \Delta f_{\mathrm{shift}}.
$$

At each recovered symbol centre, apply a 1024-sample Hann window to the side channel, zero-pad to 8192 samples, find the strongest FFT peak between 1100 and 2000 Hz, and refine the peak with three-point interpolation of log magnitudes. Those readings are stored in `symbols.csv`.

Fit the measurements jointly to:

$$
f_i = b + s\,q_i + A\sin(\omega t_i),
$$

where $q_i$ is the recovered bit. For each trial angular frequency, solve a three-column linear least-squares problem for $b$, $s$, and $A$. The script searches 0.05–0.5 rad/s in 0.0001 rad/s steps, then refines within 0.0001 rad/s of the best candidate in 0.000001 rad/s steps. It excludes the first and last 250 ms from this fit.

The verified output is:

| Parameter | Fitted value |
|---|---:|
| Base frequency | 1349.99955 Hz |
| Tone spacing | 399.99979 Hz |
| Drift amplitude | 65.00051 Hz |
| Angular frequency | 0.219911 rad/s |
| Drift frequency | 0.03499992 Hz |
| Corresponding full drift period | 28.57149 s |

The burst lasts approximately 10.634 seconds, shorter than that drift period. These estimates use the memo's sine model and zero-phase time origin; they are not all direct cursor readings. The last decimal places reflect numerical processing of this deterministic synthetic recording. Pixel measurements in the GUI have lower precision. Decoding only needs tone separation and symbol timing, so fitting the drift is optional for flag recovery.

**Descramble and validate the packet:**  
The engineer dialogue identifies the polynomial $x^7 + x^4 + 1$ and the seven-bit all-ones starting state, `0x7F`. The memo specifies MSB-first order and says the length, payload, and checksum pass through the whitener as one continuous stream. Reset the LFSR immediately after the 13 unwhitened preamble bits, then use this recurrence:

```python
feedback = ((state >> 6) ^ (state >> 3)) & 1
plain_bit = received_bit ^ feedback
state = ((state << 1) | feedback) & 0x7F
```

The exact recurrence matters: naming a polynomial alone leaves implementation conventions open. Here the mask is the XOR of state bits 6 and 3, produced before shifting left. Scrambling and descrambling use the same additive mask.

Group the descrambled stream into bytes, taking the first bit as the most significant bit. The first byte is `0x2E`, so the next 46 bytes are the payload. The following byte is the CRC:

```text
Length:     2e
Payload:    kernel{s0undw4v3s?_d1dn7_kn0w_7h3y_h4v3_h4nd5}
CRC:        55
```

Both length and CRC are one byte, or eight bits. The packet contains 48 whitened bytes: one length byte, 46 payload bytes, and one CRC byte. With the 13-bit preamble, its total is:

$$
13 + 8(1 + 46 + 1) = 397\text{ symbols}.
$$

CRC-8/SMBus uses polynomial `0x07`, initial value `0x00`, no reflected input or output, and final XOR `0x00`. Compute it over the 46 payload bytes only. The calculated value is `0x55`, matching the received checksum. The length byte is whitened but is not covered by this challenge's CRC calculation.

**Expected solver output:**  
Running `python3 solution/solve.py release/scada_emergency_capture.wav` produces:

```text
[-] Loading audio file: release/scada_emergency_capture.wav
    Sample rate: 48000 Hz | Channels: 2 | Duration: 75.0s
[-] Step 1: Computing Mid/Side Side channel S(t) = (L - R) / 2...
[-] Step 2: Applying bandpass filter (1100 Hz - 2000 Hz)...
[-] Step 3: Computing instantaneous frequency via FM discriminator...
[-] Step 4: Symbol clock grid: 37.33 Baud (1285.714 samples/symbol)...
    Scanning burst window: 0.00s to 29.50s
[+] Frame lock at sample 887680 (t = 18.493s | Barker score = 13.0)
[+] CRC-8/SMBUS check: VALID (0x55)

```

## Flag
==================================================
[+] FLAG: kernel{s0undw4v3s?_d1dn7_kn0w_7h3y_h4v3_h4nd5}
==================================================

The reference solver reads up to 400 symbols after a preamble candidate, enough for this 397-symbol packet, then uses the decoded length to locate the CRC. The measurement script instead determines the length first and reads exactly the corresponding packet size.

If the result differs, first compare the input SHA-256. A stale WAV can contain the earlier flag and a shorter burst. Keep the recording stereo for decoding; mixing it to mono before subtraction suppresses the differential telemetry. For visual inspection, use the exported mono `band.wav`, whose subtraction has already been performed.
