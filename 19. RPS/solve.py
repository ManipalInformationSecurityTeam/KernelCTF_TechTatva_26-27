#!/usr/bin/env python3
"""Solve the current RSP session using its 50 observed moves.

Usage: python3 solve.py HOST PORT, or python3 solve.py --local.
Build the organizer's C seed search with `make solve_c` first.
"""

import argparse
import re
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROUND = re.compile(rb"^Round (\d{2}): CPU -> (ROCK|PAPER|SCISSORS)$", re.MULTILINE)
MOVES = {b"ROCK": "R", b"PAPER": "P", b"SCISSORS": "S"}
PROMPT = b">> "
TIMEOUT = 30


def observations(transcript):
    rounds = ROUND.findall(transcript)
    if len(rounds) != 50 or [int(number) for number, _ in rounds] != list(range(1, 51)):
        raise ValueError(f"Expected rounds 01–50, found {len(rounds)} valid rounds")
    return "".join(MOVES[name] for _, name in rounds)


def predict(moves):
    solver = ROOT / "solve_c"
    if not solver.is_file():
        raise FileNotFoundError("Missing solve_c; run `make solve_c` first")
    result = subprocess.run(
        [str(solver), moves], capture_output=True, text=True, timeout=TIMEOUT
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Seed search failed")
    prediction = result.stdout.strip()
    if len(prediction) != 10 or any(move not in "RPS" for move in prediction):
        raise RuntimeError(f"Invalid solver output: {prediction!r}")
    print(result.stderr.strip(), file=sys.stderr)
    print(f"Predicted rounds 51–60: {prediction}")
    return prediction


def solve_remote(host, port):
    with socket.create_connection((host, port), timeout=TIMEOUT) as connection:
        connection.settimeout(TIMEOUT)
        transcript = bytearray()
        while PROMPT not in transcript:
            chunk = connection.recv(4096)
            if not chunk:
                raise RuntimeError("Server closed before the prediction prompt")
            transcript.extend(chunk)
        moves = observations(transcript)
        print(f"Collected {len(moves)} observations from {host}:{port}")
        connection.sendall((predict(moves) + "\n").encode())
        response = bytearray()
        while chunk := connection.recv(4096):
            response.extend(chunk)
        print(response.decode(errors="replace"), end="")
        if b"[+] FLAG:" not in response:
            raise RuntimeError("Server did not return a flag")


def solve_local():
    binary = ROOT / "RSP"
    if not binary.is_file():
        raise FileNotFoundError("Missing interactive RSP; run `make RSP` first")
    process = subprocess.Popen(
        [str(binary)], cwd=ROOT, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
    )
    try:
        transcript = bytearray()
        while PROMPT not in transcript:
            chunk = process.stdout.read(1)
            if not chunk:
                raise RuntimeError("Challenge closed before the prediction prompt")
            transcript.extend(chunk)
        moves = observations(transcript)
        print(f"Collected {len(moves)} local observations")
        response, errors = process.communicate((predict(moves) + "\n").encode(), timeout=TIMEOUT)
        if process.returncode:
            raise RuntimeError(errors.decode(errors="replace") or response.decode(errors="replace"))
        print(response.decode(errors="replace"), end="")
        if b"[+] FLAG:" not in response:
            raise RuntimeError("Challenge did not return a flag")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", nargs="?", default="127.0.0.1")
    parser.add_argument("port", nargs="?", type=int, default=1337)
    parser.add_argument("--local", action="store_true", help="solve the interactive executable directly")
    args = parser.parse_args()
    try:
        if args.local:
            solve_local()
        else:
            solve_remote(args.host, args.port)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"solve.py: {error}\n")


if __name__ == "__main__":
    main()
