# Order Matters — Baby-Steps Clue Path

## The correct website order

`A → D → K → B → H → F → M → C → J`

Don't click every box just to see what it says: the website treats a wrong *new* selection as a poisoned run. Reopening a box you've already selected is okay. To recover from a wrong selection, use **Reset Challenge** to restart the whole run.

## Baby steps: box by box

### 1. A — Intake ledger → D — Contact print

**Hint on A:** There are 43 positions but only 42 are present. Two images share the same camera mark, so compare the frame and exposure time instead of trusting the filename.

**What that means:** One frame is missing. The camera name alone won't tell you which image is the real one; the frame number and timestamp need to match the intake record.

**In Wireshark:**

1. Keep the display filter set to `http`.
2. Find the request `/intake/receipt/1842`. The reply says `frame_count: 43`, `missing_frame: 27`, camera `archive-cam-17`, and stamp `03:17:42`.
3. To inspect the images carried inside the PCAP, choose **File → Export Objects → HTTP**. Save `contact-print.png` and `contact-print-copy.png`.
4. The correct contact print has camera `archive-cam-17`, frame `27`, register `violet-lower-left`, and exposure `03:17:42`.
5. The copy says register `copied` and its exposure is `03:12:04`, so it doesn't match the intake event.

**Why D:** D is the Contact Print, and the matching evidence is frame 27 with the correct exposure time—not the older copy.

### 2. D — Contact print → K — Damaged negative

**Hint on D:** The big violet mark appears on multiple prints. The useful clue is a smaller edge mark on the “second-return” object.

**What that means:** Ignore the large violet mark; it was copied onto more than one image. Look for the smaller mark that belongs specifically to the second scan/return.

**In Wireshark:**

1. In **File → Export Objects → HTTP**, save `negative-27.png`.
2. Inspect its PNG text metadata. It contains `Plate: 27`, `Dye: violet`, `EdgeMark: 6b2a`, and `ScanPass: second-return`.

**Why K:** K is the Damaged Negative. Its unique edge mark is `6b2a`, and its scan pass is `second-return`. Keep `6b2a` for the next step.

### 3. K — Damaged negative → B — Resolver slip

**Hint on K:** The edge code appears in more than one place. One appearance is a DNS question ID, and another is in a receipt. A nearby probe reuses part of the timing, so compare direction, TTL, and return timing—not just the number.

**What that means:** The number `6b2a` alone isn't proof. Find the DNS conversation with that ID and make sure the rest of its details match the active evidence trail.

**In Wireshark:**

1. Replace the filter with `dns`.
2. Find the DNS query for `plate-27.aeb.test`. Its DNS transaction ID is `0x6b2a`.
3. Check the matching reply, not an unrelated query with a similar ID. The related resolver receipt is `/resolver/receipt/6b2a`; its body records `xid: 0x6b2a`, `ttl: 73`, `delta_ms: 37`, `operator_mark: G-3`, and `reply_path: forward`.
4. The negative's edge mark `6b2a` matches that DNS transaction ID. The direction/TTL/timing details confirm the related exchange.

**Why B:** B is the Resolver Slip. It concerns the DNS exchange and warns that a transaction ID can be reused, so the whole exchange must match.

### 4. B — Resolver slip → H — Margin transcript

**Hint on B:** A 37-millisecond gap appears twice. Only one event belongs to the active operator shift. Compare the marginal notation with the exchange's direction and provenance.

**What that means:** Don't follow `37 ms` by itself. A decoy phone/switchboard record also says 37 ms. The relevant record is the DNS/resolver exchange you just matched, with operator mark `G-3` and the correct forward reply path.

**In Wireshark:**

1. With `http` as the display filter, find `/resolver/receipt/6b2a` and note the `37 ms` gap and `G-3` operator mark.
2. Compare it with `/switchboard/trunk/12`, which also says `duration=37ms`. That record is just a trunk call and doesn't have the matching resolver provenance.
3. The hint tells you to follow the associated margin notation. The next record in the real trail is the margin transcript.

**Why H:** H is the Margin Transcript. Its three marks are `09 / graphite / return`.

### 5. H — Margin transcript → F — Transfer manifest

**Hint on H:** The marks `09 / graphite / return` are described as a short dispatch code. A competing record repeats the number 9 but substitutes a physical measurement for the transferred object's size.

**What that means:** Translate the three marks into the dispatch shorthand `9-G-R`. Then find the transfer record for route 09. Don't confuse a transferred object's byte size with a courier's weight in grams.

**In Wireshark:**

1. With `http` as the filter, find `/journal/margin/folio-3`. Its body contains `09 / graphite / return`.
2. Find `/transfer/route/09`. Its JSON says `route: 9`, `object: segment-c`, `size: 720`, `source: archive-mirror`, `dispatch_code: 9-G-R`, and `digest_prefix: b4d1`.
3. Compare it with `/courier/claim/bay6`, which says `weight_g: 720`. That 720 is a physical weight, not the object's size, and its seal is marked reused.

**Why F:** F is the Transfer Manifest. The `9-G-R` dispatch code and object size of 720 are the matching evidence.

### 6. F — Transfer manifest → M — Memory ledger

**Hint on F:** The digest prefix appears in both a later dump and an older copy. Check the object's parent/source and exact byte count. The copied record is one byte shorter.

**What that means:** The checksum prefix `b4d1` is shared by the real record and a decoy. Use the size and source/parent to decide which is real.

**In Wireshark:**

1. `/transfer/route/09` gives the real object's size as **720 bytes** and source `archive-mirror`.
2. `/transfer/route/09-retry` is the decoy: it has size **719**, object `segment-c-copy`, source `coldstore`, and the same tempting digest prefix `b4d1`.
3. Follow the real 720-byte `segment-c` object into the memory record.

**Why M:** M is the Memory Ledger, and the matching memory segment should have the same 720-byte length and the correct archive-mirror parent.

### 7. M — Memory ledger → C — Fragment register

**Hint on M:** The offset alone is not enough because multiple ranges overlap. Match the size and terminal lineage.

**What that means:** Both the real segment and a copied segment can use the same offset. Use all the fields together: offset **and** length **and** parent/process lineage.

**In Wireshark:**

1. Find `/memory/segment/C`. The real record says offset `0x01e2`, length `720`, parent `archive-mirror`, and process tag `17-04-11`.
2. The decoy `/memory/segment/C-copy` uses the same offset but length `719`, parent `coldstore`, and process tag `17-04-10`.
3. Find `/register/fragments`. It has `slot 04: offset=0x01E2 length=720` and `terminal-seq=17-04-11`.

**Why C:** C is the Fragment Register. Slot 04 matches the real segment's offset, 720-byte length, and terminal sequence.

### 8. C — Fragment register → J — Terminal folio

**Hint on C:** A terminal sequence reappears in a closure record. A copy has the same-looking digest prefix but a different parent and is one byte shorter.

**What that means:** Follow the closure acknowledgement that matches the genuine segment's lineage, not the copied/shorter one.

**In Wireshark:**

1. The register gives terminal sequence `17-04-11`.
2. Find `/terminal/folio-17`. It contains `ACK 17-04-11` and `seal profile: C20P1305 / tag=16 / nonce=12`.
3. The same folio says three stamps survive: first image pass, operator return, and closure; mirror stamps are not authoritative.

**Why J:** J is the Terminal Folio. It confirms the end of the evidence chain and tells you the crypto format and sizes: ChaCha20-Poly1305, a 16-byte tag, and a 12-byte nonce.

## After J: recover the key and nonce from the PCAP

J's hint says the capture contains two useful types of data:

- **HTTP ETags**: the four correct responses contain the key in four chunks.
- **DNS TXT records**: three records contain the nonce in three chunks.

### 9. Build the 32-byte key from four HTTP ETags

In Wireshark, type `http`, then inspect each response's **ETag** header for these exact request paths. Remove the quotation marks around the ETag values; don't include the header name or quotes.

| HTTP path | ETag chunk to copy |
|---|---|
| `/images/negative-27.png` | `e5fbcfefdb7669c6` |
| `/journal/margin/folio-3` | `8f0cfc988d8d9802` |
| `/transfer/route/09` | `b181a6eb80dc73b5` |
| `/memory/segment/C` | `6e7c5b0e6f8fffad` |

Join those four chunks in exactly that order, with no spaces:

`e5fbcfefdb7669c68f0cfc988d8d9802b181a6eb80dc73b56e7c5b0e6f8fffad`

That is 64 hex characters = 32 bytes. Don't use the ETags from every HTTP response; only these four resources belong to the surviving evidence chain.

### 10. Build the 12-byte nonce from three DNS TXT values

In Wireshark, replace the filter with `dns`. Look for the exact DNS names below and read the TXT **answer**. Copy only the eight hex characters after the named field—not the other text in the TXT answer.

| DNS name | Field to take | Correct value | Ignore this lookalike |
|---|---|---|---|
| `lease-03.aeb.test` | `stamp` | `cb642d47` | `lease-03-mirror.aeb.test` has `7e70ff35` |
| `return-ledger-11.aeb.test` | `mark` | `26458283` | `return-ledger-copy.aeb.test` has `97c1d74a` |
| `folio-imprint-17.aeb.test` | `imprint` | `1e08567a` | `folio-imprint-copy.aeb.test` has `4efc4cc5` |

Why those three? J says the valid stamps are from the **first image pass**, **operator return**, and **closure**. The real records have modes `warm`, `return`, and `close`; mirror/copy records are decoys.

Join only the three correct values in that order, with no spaces:

`cb642d47264582831e08567a`

That's 24 hex characters = 12 bytes, the nonce length stated in J.

## Collect the nine website fragments

The fragment hex comes from the **website**, not from the PCAP. Select the evidence boxes in this exact order and copy each displayed fragment:

| Order | Box | Fragment |
|---:|---|---|
| 1 | A | `acae63346a` |
| 2 | D | `d52c5dc6be` |
| 3 | K | `d4365dd2b0` |
| 4 | B | `fccb5e5a99` |
| 5 | H | `1a38e470ea` |
| 6 | F | `828af924` |
| 7 | M | `a73dc0f1` |
| 8 | C | `fae2a98f` |
| 9 | J | `dcc63417` |

Join them with **no spaces and no separators**:

`acae63346ad52c5dc6bed4365dd2b0fccb5e5a991a38e470ea828af924a73dc0f1fae2a98fdcc63417`

Convert the joined hex string to bytes once. Do not decode each fragment separately.

## Final step: decrypt

The terminal folio names **ChaCha20-Poly1305**. The combined ciphertext includes its 16-byte authentication tag at the end, so do not remove the last 16 bytes before decrypting.

If you have Python and the `cryptography` package installed, run this:

```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

ciphertext = bytes.fromhex(
    "acae63346ad52c5dc6bed4365dd2b0fccb5e5a991a38e470ea"
    "828af924a73dc0f1fae2a98fdcc63417"
)
key = bytes.fromhex(
    "e5fbcfefdb7669c68f0cfc988d8d9802"
    "b181a6eb80dc73b56e7c5b0e6f8fffad"
)
nonce = bytes.fromhex("cb642d47264582831e08567a")

print(ChaCha20Poly1305(key).decrypt(nonce, ciphertext, None).decode())
```

If Python says `ModuleNotFoundError: No module named 'cryptography'`, install it with `python -m pip install cryptography` and run the script again.

If decryption fails, check these three things first: the nine fragments are in the exact box order above; the four ETags were concatenated in the listed order; and the DNS values came from the three exact names, not their mirrors/copies.

### Flag

`kernel{d1ct4t0r_4hh_pc4p}`
