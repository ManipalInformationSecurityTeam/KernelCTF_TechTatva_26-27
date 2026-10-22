# Order Matters

## Jane7710

## WebEx + Forensics

## Medium

### Question Description

Fifteen pieces of evidence remain, scattered across a collection of files. Some matter. Some don't. And somewhere in the mess, someone made sure that the truth wouldn't be so easy to find.
Evidence doesn't always lie. Sometimes, you just look at it the wrong way.
There's a reason certain things were left behind. There's a reason others were never meant to be found.
Choose carefully. You don't get to take it back. One error, your efforts go meaningless.

**Order matters.**

### Files needed
1. Players open the website and read the warning: selecting an incorrect new piece of evidence permanently poisons the run. They can reset the entire challenge but cannot undo an individual selection.

2. Players inspect all 15 evidence boxes. E, G, I, L, N, and O are decoys. The remaining clues rely on comparing image details, DNS exchanges, timing, dispatch shorthand, object sizes, and record lineage.

3. A, the Intake Ledger, reports 43 positions but only 42 present, identifying missing frame 27. Comparing the frame, registration mark, and exposure interval leads to D, the Contact Print.

4. D contains a broad violet mark and a smaller edge mark on the second-return object. Following the smaller mark leads to K, the Damaged Negative.

5. K reveals that the edge code appears in multiple places, including a DNS question ID and a receipt. Comparing DNS direction, TTL, and response timing identifies B, the Resolver Slip.

6. B notes two occurrences of the same 37-millisecond gap. Matching provenance and marginal notation leads to H, the Margin Transcript, rather than the similar-looking retry.

7. H contains `09 / graphite / return`, corresponding to dispatch shorthand `9-G-R`. Distinguishing transferred-object bytes from courier weight identifies F, the Transfer Manifest.

8. F points to a repeated digest prefix. Comparing parent lineage and byte count—720 bytes versus the copied record's 719—identifies M, the Memory Ledger.

9. M warns that several index ranges overlap. Matching the 720-byte length and terminal lineage leads to C, the Fragment Register.

10. C identifies a terminal sequence that reappears in the closure record. Rejecting the wrong parent lineage and one-byte mismatch leads to J, the Terminal Folio.

11. J explains that the nine fragments form one authenticated ChaCha20-Poly1305 stream. Players need a 32-byte key, a 12-byte nonce, and the complete ciphertext including its 16-byte authentication tag.

12. Players inspect `CASE_1842.pcap` and recover the key from four HTTP ETags, concatenated in this order:

    - `/images/negative-27.png` — `e5fbcfefdb7669c6`
    - `/journal/margin/folio-3` — `8f0cfc988d8d9802`
    - `/transfer/route/09` — `b181a6eb80dc73b5`
    - `/memory/segment/C` — `6e7c5b0e6f8fffad`

    **Full key:**

    `e5fbcfefdb7669c68f0cfc988d8d9802b181a6eb80dc73b56e7c5b0e6f8fffad`

13. Players recover the nonce from three correlated DNS TXT fields:

    - `lease-03.aeb.test`, `stamp` — `cb642d47`
    - `return-ledger-11.aeb.test`, `mark` — `26458283`
    - `folio-imprint-17.aeb.test`, `imprint` — `1e08567a`

    **Full nonce:** `cb642d47264582831e08567a`

14. Players select the correct evidence in order: `A → D → K → B → H → F → M → C → J`. They concatenate these fragments without spaces or separators:

    - A — `acae63346a`
    - D — `d52c5dc6be`
    - K — `d4365dd2b0`
    - B — `fccb5e5a99`
    - H — `1a38e470ea`
    - F — `828af924`
    - M — `a73dc0f1`
    - C — `fae2a98f`
    - J — `dcc63417`

    The joined hex is converted to bytes once and decrypted using ChaCha20-Poly1305 with the recovered key and nonce. The 16-byte authentication tag remains attached. Incorrect fragments, ordering, or PCAP values cause authentication to fail.

15. Successful decryption returns the flag:

    `kernel{d1ct4t0r_4hh_pc4p}`

### Flag

`kernel{d1ct4t0r_4hh_pc4p}`
