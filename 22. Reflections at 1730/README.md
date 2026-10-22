# Reflections at 17:30

## Author
DeliverHellVeil

## Domain
Forensics / Steganography

## Difficulty
Medium-Hard

### Question Description

An item vanished from the back-wall display shelf during the afternoon shift. Security recovered a single frame, `cam_frame_0730.jpg`, from the entrance camera at the moment the suspect was standing near the counter. However, the camera's privacy filter has obscured the shelf display, and the incident backup appears to be bundled inside the capture file.

Your objective is to reconstruct the display, unlock the point-of-sale (POS) ledger, and identify the **receipt ID of the active transaction** for the missing item at the exact moment the frame was captured.

**Files to be provided:**

- `cam_frame_0730.jpg`

### Intended Solution

Open `cam_frame_0730.jpg` in an image viewer. The image shows a grainy, green-tinted CCTV frame from `CAM_01 [ENTRANCE]`, with a timestamp of `2026-03-14 17:30:00`.

Two details stand out: the three rows of display shelves are obscured by colored static bars, and the `EXIT` sign appears backward as `TIXE`, indicating a mirrored camera feed.

Inspect the file's metadata and embedded structure using ExifTool and Binwalk:

```
exiftool cam_frame_0730.jpg
binwalk cam_frame_0730.jpg
```

The EXIF metadata contains the description:

```
Image Description : Planogram: v3 (Exclusive)
```

Binwalk reveals that the file contains multiple embedded components:

1. JPEG image data beginning at offset `0x0`.
2. PNG image data with dimensions `1920 x 1080`, appended after the JPEG End-of-Image marker (`FF D9`).
3. ZIP archive data appended after the PNG stream, containing `planogram_v3.png`, `notes.txt`, and `ledger.zip`.

These findings indicate that the image contains additional evidence that must be extracted before the shelves can be reconstructed.

**Extract the embedded files:**  
Use Foremost to carve the embedded files from the original image:

```
foremost -i cam_frame_0730.jpg -o extracted_files
```

Alternatively, use Binwalk:

```
binwalk -e cam_frame_0730.jpg
```

If necessary, extract the PNG layer manually using Python by locating the PNG signature and the end of its `IEND` chunk:

```
with open("cam_frame_0730.jpg", "rb") as f:
    data = f.read()

png_start = data.find(b"\x89PNG\r\n\x1a\n")
png_end = data.find(b"IEND", png_start) + 8

with open("shelf_mask.png", "wb") as f:
    f.write(data[png_start:png_end])
```

Inspect the extracted files. The `notes.txt` file contains the following clues:

> Camera clock runs +11 minutes ahead. The mirror is convex and fitted opposite the back wall. The planogram diagram shows every slot in reading order: left to right, top to bottom. It's an exclusive display—two halves that cancel each other out. The ledger is keyed to the item that went missing.

The `planogram_v3.png` file contains a schematic of the 3 × 4 display shelf, mapping twelve slots to their respective SKUs:

| Shelf | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
| --- | --- | --- | --- | --- |
| Top | `A1F3` | `B7K2` | `C9D4` | `E0M8` |
| Middle | `H5J1` | `K3P6` | `Q8R2` | `T4W9` |
| Bottom | `X2Y7` | `Z6N0` | `L1U5` | `G3V8` |

The remaining file, `ledger.zip`, is an encrypted archive containing `pos_ledger.csv`.

**Reconstruct the redacted shelf using XOR:**  
Open `shelf_mask.png`. It appears mostly black, with three horizontal strips of colored noise matching the locations of the redacted shelves. Neither the original JPEG nor the extracted PNG independently reveals the hidden shelf labels.

The metadata description `Planogram: v3 (Exclusive)` and the note about two halves cancelling each other out suggest the use of an **Exclusive OR (XOR)** operation.

Combine the original JPEG and the extracted PNG using bitwise XOR to cancel out the noise and restore the obscured shelf display.

Alternatively, use Python:

```
import numpy as np
from PIL import Image, ImageOps

# Load the original camera frame and extracted mask
jpg_arr = np.array(
    Image.open("cam_frame_0730.jpg").convert("RGB")
)
mask_arr = np.array(
    Image.open("shelf_mask.png").convert("RGB")
)

# XOR the two image layers
unredacted_arr = np.bitwise_xor(jpg_arr, mask_arr)
unredacted_img = Image.fromarray(unredacted_arr)
unredacted_img.save("unredacted_mirror.png")

# Correct the mirrored orientation
true_wall_img = ImageOps.mirror(unredacted_img)
true_wall_img.save("solved_wall_true_orientation.png")
```

The resulting image reveals the shelf display. The horizontal flip is necessary because the convex mirror reverses the left-to-right orientation of the back wall.

Inspect the reconstructed image in its corrected orientation. The empty slot is on the middle shelf, in the third column from the left.

The backward `TIXE` sign and the reversed plaque text confirm that the original camera view is mirrored. After correcting the orientation, the empty position corresponds to Slot #07 in the planogram's left-to-right, top-to-bottom reading order.

Cross-reference Slot #07 with `planogram_v3.png`:

- **Missing slot:** `SLOT #07`
- **Missing SKU:** `Q8R2`

The missing SKU is also the password needed to unlock the encrypted POS ledger.

**Unlock the POS ledger:**  
Use `Q8R2` as the password to extract `ledger.zip`:

```
unzip -P Q8R2 ledger.zip
cat pos_ledger.csv
```

The extracted CSV contains the following transaction history:

```
receipt_id,timestamp,event,sku,ref
R-0301,2026-03-14 09:12:40,SCAN,K3P6,
R-0588,2026-03-14 15:30:05,SCAN,Q8R2,
R-0592,2026-03-14 15:45:10,REFUND,Q8R2,R-0588
R-0701,2026-03-14 16:58:22,SCAN,Q8R2,
R-0703,2026-03-14 17:05:40,VOID,Q8R2,R-0701
R-0744,2026-03-14 17:15:02,SCAN,K3P6,
R-0766,2026-03-14 17:17:40,SCAN,Q8R2,
R-0770,2026-03-14 17:20:10,VOID,Q8R2,R-0766
R-0771,2026-03-14 17:20:30,SCAN,Q8R2,
```

The ledger contains multiple scans of the missing SKU, but earlier transactions were subsequently refunded or voided. The correct receipt must be identified by correlating the camera timestamp with the transaction history.

**Correct the timestamp and identify the active receipt**  
The camera's on-screen timestamp reads:

```
2026-03-14 17:30:00
```

According to `notes.txt`, the camera clock runs 11 minutes ahead. Subtract 11 minutes to obtain the actual capture time:

$$
17{:}30{:}00 - 00{:}11{:}00 = 17{:}19{:}00
$$

The actual frame capture time is therefore `2026-03-14 17:19:00`.

Now examine the ledger entries for SKU `Q8R2`:

- **R-0588 — 15:30:05:** The item is scanned, but the transaction is refunded at 15:45:10 under receipt `R-0592`.
- **R-0701 — 16:58:22:** The item is scanned, but the transaction is voided at 17:05:40 under receipt `R-0703`.
- **R-0766 — 17:17:40:** The item is scanned 1 minute and 20 seconds before the corrected camera capture time.
- **R-0770 — 17:20:10:** The transaction associated with `R-0766` is voided, after the frame was captured.
- **R-0771 — 17:20:30:** The item is scanned again, also after the frame was captured.

At `17:19:00`, receipt `R-0766` is the active transaction for the missing SKU. Its later void does not change its status at the time the frame was captured.

The receipt ID forms the flag.

### Flag

> `kernel{R-0766}`