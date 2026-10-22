# RPS

## Author
yam1

## Domain
Reverse Engg / Cryptography

## Difficulty
Medium

## Challenge Description
The quantum CPU claims its Rock-Paper-Scissors moves are unpredictable. Observe 50 rounds, then predict its exact moves for rounds 51 through 60 to claim the flag. Connect with netcat to tcp.ctf.wearemist.in on port 31002.


## Intended Solution

**Recover the state algorithm**  
Inspect the executable in a disassembler. The hash routine contains the characteristic xxHash64 primes, including `0x9E3779B185EBCA87` and `0xC2B2AE3D27D4EB4F`. Follow the caller that generates the 50 visible moves. It reads three random bytes into a 32-bit value, masks the result to 24 bits, initializes a 64-bit state, and advances that state once per round.

The constants and state transitions are:

```text
seed       ∈ [0, 0xFFFFFF]
SEED_SALT  = 0x5EEDF00DDEADBEEF
STATE_SALT = 0x1337C0DEC001CAFE

S₀ = XXH64(8-byte little-endian seed, SEED_SALT)
Sᵣ = XXH64(8-byte little-endian Sᵣ₋₁, STATE_SALT)
moveᵣ = Sᵣ mod 3

0 → R (ROCK), 1 → P (PAPER), 2 → S (SCISSORS)
```

The `XXH64` calls hash an eight-byte value. The salts are passed as the hash seed argument; they are not appended to the input. The generated starting seed is random for each process and does not appear as a fixed value in the binary.

**Recover the session seed**  
Connect to the service and keep that connection open. Convert its 50 displayed moves to a string of `R`, `P`, and `S`. For each of the `2²⁴ = 16,777,216` candidate seeds, reproduce the state transitions and compare the resulting moves in order. Stop checking a candidate as soon as one move differs. A compiled solver makes this search practical within the service's 30-second session limit.

```text
for seed in 0..0xFFFFFF:
    state = XXH64(seed, SEED_SALT)
    for observed_move in observations:
        state = XXH64(state, STATE_SALT)
        if "RPS"[state % 3] != observed_move:
            reject seed
            break
    if all 50 moves match:
        use this state as S₅₀
        break

repeat 10 times:
    state = XXH64(state, STATE_SALT)
    append "RPS"[state % 3] to the prediction
```

Each observed move usually removes about two thirds of the remaining candidates. The 50 observations are more than enough to distinguish a seed in this 24-bit search space. Send the ten predicted letters, with no spaces, on the same connection that supplied the observations.

**Run the organizer solution**  
The supplied [solve.c](solve.c) implements the seed search in C with OpenMP. [solve.py](solve.py) reads the service output, calls that solver, and submits the predicted sequence.

```sh
make solve_c
python3 solve.py HOST PORT
```

For the interactive executable in the project root, use `python3 solve.py --local`. The player package's reference executable exits after showing its moves, so it cannot award the flag. On the service, a correct prediction reaches round 60 and the program prints the reward read from the server's 

## Flag
> kernel{1_f33l_l1k3_p4tr1ck_j4n3}
