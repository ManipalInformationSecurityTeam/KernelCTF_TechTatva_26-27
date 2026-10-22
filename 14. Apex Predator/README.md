# Apex Predator

## Author
1-4m-5p33d

## Domain
Forensics / OSINT

## Difficulty
Medium

### Question Description

The drop happens fast. If you miss the apex on the crest, gravity takes over before you even touch the pedal.

We intercepted a data package from a private track day. Something's hidden in the run. Find the crest, find the landing, find what controls the pedals.

#### Provided Files:
- `telemetry.csv` — Raw vehicle telemetry log recording vehicle dynamics (timestamps, coordinates, altitude, lateral G-forces).
- `apex_frame.png` — Cockpit photograph captured during the track session.
- `message.txt.gpg` — GPG-encrypted file containing the flag.

### Intended Solution

This challenge chains three disciplines together: **steganography** (extracting a hidden clue from an image), **data forensics** (isolating an anomaly in vehicle telemetry logs), and **OSINT** (correlating GPS coordinates with real-world landmarks and sponsor branding). The three provided files are interdependent: `apex_frame.png` provides the telemetry anchor, `telemetry.csv` yields the coordinates, the coordinates pinpoint the real-world location, and the landmark provides the passphrase material to decrypt `message.txt.gpg`.

#### Step 1: Image Reconnaissance & Steganography

Initial inspection of `apex_frame.png` using standard metadata tools (`exiftool`, `file`) does not show explicit GPS coordinates or comments. However, inspecting the image visually reveals a track outline decal on the cockpit tub corresponding to **WeatherTech Raceway Laguna Seca**.

Running an exhaustive LSB steganography scan with `zsteg`:

```bash
zsteg -a apex_frame.png
```

This reveals hidden text in the `b1,bgr,lsb,xy` plane:

```text
Lateral G: 1.4G. Vertical drop: 5 stories.
Check telemetry row 1832 for the crest vector.
When you land on the barrier below, look for what controls the pedals.
```

The steganographic message provides three vital clues:
1. Row 1832 in `telemetry.csv` holds the key vector.
2. The physical destination is described as a steep vertical drop landing on a barrier.
3. The final filter for the passphrase is "what controls the pedals".

#### Step 2: Telemetry Data Forensics

Inspect row 1832 of `telemetry.csv`, or verify the elevation drop programmatically using Python and pandas:

```python
import pandas as pd

df = pd.read_csv("telemetry.csv")
df["alt_delta"] = df["Altitude"].diff()
steepest_drop = df.loc[df["alt_delta"].idxmin()]
print(steepest_drop)
```

At row 1832, we observe the sharpest sustained elevation drop in the dataset:

```text
Timestamp,Lat,Long,Altitude,G_Lat
12.43,36.5848278,-121.7490265,241.2,1.40
12.44,36.5848278,-121.7490265,232.1,1.42   <-- sharpest drop (row 1832)
```

The extracted GPS coordinates are:
- **Latitude:** `36.5848278`
- **Longitude:** `-121.7490265`

#### Step 3: OSINT & Geolocation Analysis

Plotting `36.5848278, -121.7490265` into Google Maps and examining Google Street View places the viewpoint directly at the crest and descent of the legendary **Corkscrew** (Turns 8 and 8A) at **WeatherTech Raceway Laguna Seca**, known for its 5-story drop and extreme lateral Gs.

Examining the trackside barriers at the base/landing of the Corkscrew reveals multiple sponsor banners:
- Le Mans Series
- Patrón
- Advan
- **Piloti**

Using the thematic clue *"look for what controls the pedals"*, we evaluate the sponsors:
- Patrón: Tequila brand.
- Advan: Tire manufacturer.
- Le Mans Series: Racing championship.
- **Piloti**: Renowned performance motorsport driving shoes. Drivers use shoes to control the pedals.

#### Step 4: GPG Decryption

The passphrase follows the format `brand_producttype` (all lowercase, separated by an underscore):

```text
piloti_drivingshoes
```

Decrypt `message.txt.gpg` with GPG:

```bash
gpg -d --passphrase "piloti_drivingshoes" --batch message.txt.gpg
```

Output:
```text
kernel{c0rk5cr3w_5_st0ry_dr0p_p1l0t1}
```

### Flag

> `kernel{c0rk5cr3w_5_st0ry_dr0p_p1l0t1}`
