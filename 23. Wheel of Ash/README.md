# Wheel of Ash

## cipher_muse777

## Cryptography

## Hard/Medium

### Question Description
An Echo circles an Origin that refuses to be found. You may ask your questions, but the answer will never be the one you seek. Listen carefully; even a single bit can betray what silence tries to protect.

### Intended Solution
- players are given the RSA public parameters (n) and (e), along with the Echo ciphertext and the value of the Measure (R).
- The first important observation is that the Echo is not the original secret. It is related to the hidden Origin by:
```
  M2=(M1+R) mod n
```
where (M1) is the Origin and (M2) is the Echo.
- The Echo is RSA-encrypted using the normal RSA formula:
```
C = M2^e mod n
```
- We cannot directly decrypt C, because the private RSA key is not given.
- However, the server provides the comparison oracle. We can choose any value (x), encrypt it ourselves using the public key:
```
Cx = x^e mod n
```
and send (Cx) to the oracle.
- The server decrypts our ciphertext to recover (x), then compares (x) with the hidden (M2) on a modular circle.
- The oracle calculates:
```
d = (x - M2) mod n
```
- This value is then converted into a centered modular difference. For an odd modulus (n), the positive half is determined by:
```
0 < d <= (n - 1) / 2
```
- The oracle returns True if (x) lies in this positive half relative to (M2), and False otherwise.
- This means the oracle gives us only one bit of information per query, but carefully chosen (x) values let us bisect the possible locations of (M2).
- We repeatedly choose values near the middle of the remaining search range and observe whether the oracle returns True or False.
- Eventually, the queries narrow down one of the TRUE/FALSE boundaries to two consecutive values.
- This boundary is not (M2) itself. Because the oracle uses a centered modular distance, the boundary is shifted from (M2) by approximately half of the modulus.
- Once the boundary is identified, we use the known modular offset to recover the exact value of (M2).
- After recovering the Echo value, we work backward using the known Measure:
```
M1 = (M2 - R) mod n
```
- This gives us the original Origin value (M1).

- Finally, (M1) is the integer representation of the flag. We convert it back into bytes using:

long_to_bytes(M1)
- The resulting bytes give the flag.
### Flag
kernel{n3v3r_7ru57_7h3_0bvi0u5}
