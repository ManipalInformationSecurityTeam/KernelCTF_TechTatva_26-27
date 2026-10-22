# Turing's Mirage

**Category:** Forensics / Reverse Engineering  
**Difficulty:** Medium-Easy  
**Flag Format:** `kernel{...}`  

## Description

During an incident response investigation, we recovered an anomalous image file named `challenge.cng` alongside a proprietary validation utility called `viewer`.

Standard image viewers fail to open the file, and modern AI automated parsing pipelines seem to hallucinate or report conflicting data.

Your mission:
1. Reverse-engineer the `viewer` binary to understand the proprietary CNG container format and validation checksums.
2. Reconstruct the original image file.
3. Extract the real flag hidden within.

## Files Provided
- `challenge.cng`: The corrupted / custom formatted image.
- `viewer`: Linux x86_64 ELF binary used to validate `.cng` files.

---
*Beware of mirages in the data stream.*

