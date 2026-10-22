#!/usr/bin/env python3
"""
solve.py - reference solver for "Chance Is a Convenient Lie".

Usage:  python3 solve.py [host] [port]      (default: localhost 5000)

Idea: Call Bluff on the first rounds of each 12-round block to see the cards,
turn them into numbers 0-51, brute-force x_next = (a*x + c) % 52, then predict
every later round and answer Truth / Call Bluff correctly.
Standard library only.
"""

import re
import socket
import sys

SYMBOLS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["\u2660", "\u2665", "\u2666", "\u2663"]          # spades, hearts, diamonds, clubs
CARD_TO_NUM = {SYMBOLS[n % 13] + SUITS[n // 13]: n for n in range(52)}
NAMES = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven",
         "Eight", "Nine", "Ten", "Jack", "Queen", "King"]
WORD_TO_RANK = {}
for i, name in enumerate(NAMES):
    WORD_TO_RANK[name] = i
    WORD_TO_RANK[name + ("es" if name.endswith("x") else "s")] = i


def candidates(seq):
    """All (a, c) pairs that explain the whole observed sequence."""
    found = []
    for a in range(52):
        c = (seq[1] - a * seq[0]) % 52
        if all((a * seq[i] + c) % 52 == seq[i + 1] for i in range(len(seq) - 1)):
            found.append((a, c))
    return found


def predict_round(seq, cands):
    """Next 3 values if every candidate agrees, else None."""
    results = set()
    for a, c in cands:
        x, out = seq[-1], []
        for _ in range(3):
            x = (a * x + c) % 52
            out.append(x)
        results.add(tuple(out))
    return list(results.pop()) if len(results) == 1 else None


def read_prompt(sock):
    """Read until the '> ' prompt (or the connection closes)."""
    data = b""
    while not data.endswith(b"> "):
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    sock = socket.create_connection((host, port))
    text = read_prompt(sock)

    seq = []        # contiguous card numbers seen/predicted in the current block
    while True:
        round_no = int(re.search(r"Round (\d+)", text).group(1))
        if (round_no - 1) % 12 == 0:          # new block: old knowledge is useless
            seq = []
        m = re.search(r"I have (\d) (\w+)\.", text)
        count, rank = int(m.group(1)), WORD_TO_RANK[m.group(2)]

        cards = predict_round(seq, candidates(seq)) if len(seq) >= 3 else None
        if cards is not None:
            truthful = [v % 13 for v in cards].count(rank) == count
            choice = "1" if truthful else "2"
            seq += cards
            print("Round %d: predicted %s -> %s" % (round_no, cards, "Truth" if truthful else "Call Bluff"))
        else:
            choice = "2"                       # learn: call bluff to see the cards
            print("Round %d: learning (Call Bluff)" % round_no)

        sock.sendall((choice + "\n").encode())
        text = read_prompt(sock)

        flag = re.search(r"kernel\{[^}]*\}", text)
        if flag:
            print("\nFLAG:", flag.group(0))
            return
        if cards is None and "actual cards were" in text:
            shown = text.split("actual cards were:")[1].split("The dealer")[0].split()
            seq += [CARD_TO_NUM[card] for card in shown]
        if not text.endswith("> "):
            print("Connection closed without a flag.")
            return


if __name__ == "__main__":
    main()

