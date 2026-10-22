# Bio-Digital Transmission

## Author
DeliverHellVeil

## Domain
Forensics

## Difficulty
Medium

### Question Description

We intercepted a strange audio signal. Intelligence suggests that this single file contains both a hidden message and the key needed to decrypt it, but the audio sounds like pure noise.

Your objective is to extract the hidden data, identify the decryption key, and decipher the flag.

**File provided:**

- `transmission.wav`

**Hint:** “A biological string can't pass the gate.”

**Tools recommended:** ExifTool, Audacity, and CyberChef.

### Intended Solution

**Step 1: Extract the Ciphertext from Metadata**

Since the challenge provides a `.wav` file, begin by inspecting its metadata for hidden information before analyzing the audio itself.

Use ExifTool from the command line:

```
exiftool transmission.wav
```

Alternatively, inspect the file's properties and details using an appropriate metadata viewer.

Examine metadata fields such as Artist, Title, and Comment. One of these fields contains a seemingly random string of text.

Record this string. It is the encrypted flag, or ciphertext, and is encrypted using a Vigenère cipher. The decryption key must be recovered from the audio.

**Step 2: Analyze the Audio Spectrogram**

Open `transmission.wav` in Audacity or another audio analysis tool. Listening to the audio directly does not reveal the hidden message, so switch to a visual representation of its frequencies.

In Audacity, open the track's dropdown menu and select **Spectrogram** view.

The spectrogram reveals distinct tones switching between four specific frequency bands. These correspond to the four DNA bases: A, G, T, and C.

By analyzing the frequencies and mapping the four levels to their respective DNA bases, read the tones chronologically to recover the following 16-character DNA sequence:

```
GAGGGGTAGACCGACT
```

**Step 3: Convert the DNA Sequence into Binary**

The hint, “A biological string can't pass the gate,” suggests that the biological sequence must be converted into a digital representation.

Since DNA has four possible bases, each base can be represented using two bits. Using the specified ascending mapping from the lowest frequency to the highest, assign the following values:

- A = `00`
- G = `01`
- T = `10`
- C = `11`

Apply this mapping to the extracted DNA sequence:

```
DNA:    G A G G G G T A G A C C G A C T
Binary: 01 00 01 01 01 01 10 00 01 00 11 11 01 00 11 10
```

Combining the two-bit values produces the complete binary string:

```
01000101010110000100111101001110
```

**Step 4: Convert the Binary Data into the Decryption Key**

Standard ASCII characters are represented using eight bits, or one byte. Since each DNA base represents two bits, group the binary sequence into sets of four DNA bases to obtain eight-bit chunks.

Convert each chunk into its corresponding ASCII character using CyberChef or another binary-to-text converter:

| Binary | DNA bases | ASCII |
| --- | --- | --- |
| `01000101` | G A G G | E |
| `01011000` | G G T A | X |
| `01001111` | G A C C | O |
| `01001110` | G A C T | N |

The resulting secret key is:

```
EXON
```

This is a fitting biological reference, as an exon is a region of DNA that is retained in a mature RNA transcript.

**Step 5: Decrypt the Flag**

With the ciphertext recovered from the file's metadata and the key extracted from the spectrogram, proceed to decrypt the message.

1. Open CyberChef.
2. Add the **Vigenère Decode** operation to the recipe.
3. Paste the ciphertext extracted in Step 1 into the input field.
4. Set the key to `EXON`.
5. Inspect the output to recover the decrypted flag.

### Flag

> `kernel{unz1pp1ng_my_g3n3s}`