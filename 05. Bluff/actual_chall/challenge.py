"""
challenge.py - game logic for "Chance Is a Convenient Lie".

No networking in this file. server.py imports it and handles the TCP side.

ORGANIZER NOTE: the dealer's "luck" is a Linear Congruential Generator (LCG):
        x_next = (a * x + c) % 52
Its parameters (a, c, start value) are re-derived every 12 rounds.
Nothing in this file is ever sent to the player except cards, claims and results.
"""

import os
import random
import secrets
import sys

# ============================================================
# CONFIGURATION  (organizer: edit this section)
# ============================================================

FLAG = "kernel{ch4nc3_1s_4_c0nv3n13nt_l13}"

# Master secret. Change it for every new deployment. Never show it to players.
# Can also be set with the environment variable CTF_MASTER_SEED.
MASTER_SEED = os.environ.get("CTF_MASTER_SEED", "change-me-before-deploying")

# True  -> every connection gets its own parameter set (derived from MASTER_SEED
#          plus a random per-connection id). Players cannot record the cards on
#          one connection and replay them on another.
# False -> every connection sees the exact same card sequence (fully reproducible
#          from MASTER_SEED alone, but a player can memorise it across connections).
PER_SESSION_PARAMS = True

# None = unlimited rounds (as specified). An integer ends a connection after that
# many rounds without the flag. See README "Known weaknesses" before using.
MAX_ROUNDS = None

# Debug output goes to the SERVER console (stderr) only, never to the player.
# Off by default. Enable with:  CTF_DEBUG=1 python3 server.py
DEBUG = os.environ.get("CTF_DEBUG", "0") == "1"

# ============================================================
# CONSTANTS (part of the locked design - do not change)
# ============================================================

MODULUS = 52
ROUNDS_PER_BLOCK = 12
CARDS_PER_ROUND = 3
STREAK_TO_WIN = 5

# a must be 1 mod 4. We also skip 13: since 13 is a factor of 52, a = 13 makes
# every rank identical after the first card, which is a useless sequence.
# (Full-period Hull-Dobell is impossible mod 52 except for a = 1, see README.)
VALID_A = [5, 9, 17, 21, 25, 29, 33, 37, 41, 45, 49]
# c must be coprime to 52
VALID_C = [c for c in range(1, MODULUS) if c % 2 == 1 and c % 13 != 0]

# ============================================================
# CARDS
# ============================================================

RANK_SYMBOLS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_NAMES = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven",
              "Eight", "Nine", "Ten", "Jack", "Queen", "King"]
SUITS = ["\u2660", "\u2665", "\u2666", "\u2663"]  # spades, hearts, diamonds, clubs


def number_to_card(value):
    """0..51 -> card text, e.g. 11 -> 'Q♠', 13 -> 'A♥'."""
    if not 0 <= value < 52:
        raise ValueError("card value out of range")
    return RANK_SYMBOLS[value % 13] + SUITS[value // 13]


def card_rank(value):
    """0..51 -> rank index 0..12 (0 = Ace, 12 = King)."""
    return value % 13


def rank_word(rank, count):
    """'Queen' / 'Queens' / 'Sixes' depending on count."""
    name = RANK_NAMES[rank]
    if count == 1:
        return name
    return name + ("es" if name.endswith("x") else "s")


def claim_text(rank, count):
    return 'I have %d %s.' % (count, rank_word(rank, count))


# ============================================================
# THE GENERATOR
# ============================================================

def lcg_next(x, a, c):
    return (a * x + c) % MODULUS


def _orbit(a, c, start):
    """All values the generator cycles through when started at `start`."""
    values = []
    x = start
    while True:
        x = lcg_next(x, a, c)
        values.append(x)
        if x == lcg_next(start, a, c) and len(values) > 1:
            values.pop()
            return values


def _is_good(a, c, start):
    """Only keep parameter sets that give an interesting card stream."""
    orbit = _orbit(a, c, start)
    ranks = set(card_rank(v) for v in orbit)
    if len(ranks) < 2:          # all ranks identical -> boring
        return False
    return len(orbit) == 12 or a == 25   # longest cycle available mod 52


GOOD_PARAMS = [(a, c, s) for a in VALID_A for c in VALID_C for s in range(MODULUS)
               if _is_good(a, c, s)]


def _debug(msg):
    if DEBUG:
        print("[debug]", msg, file=sys.stderr)


def _make_block_params(game):
    """Create the parameters for the next 12-round block (deterministic)."""
    index = len(game["params"])
    rng = random.Random("%s:%s:%d" % (game["master_seed"], game["session_id"], index))
    while True:
        a, c, seed = rng.choice(GOOD_PARAMS)
        if index == 0 or (a, c) != game["params"][-1][:2]:   # vary between blocks
            break
    game["params"].append((a, c, seed))
    _debug("session %s block %d: a=%d c=%d seed=%d" % (game["session_id"], index, a, c, seed))


def block_params(game, block):
    while len(game["params"]) <= block:
        _make_block_params(game)
    return game["params"][block]


# ============================================================
# GAME STATE AND ROUND LOGIC
# ============================================================

def new_game(master_seed=None, session_id=None, claim_seed=None):
    """Create an independent game. Each connection gets its own."""
    if master_seed is None:
        master_seed = MASTER_SEED
    if session_id is None:
        session_id = secrets.token_hex(8) if PER_SESSION_PARAMS else "shared"
    return {
        "master_seed": master_seed,
        "session_id": session_id,
        "params": [],
        "claim_rng": random.Random(claim_seed) if claim_seed is not None
                     else random.SystemRandom(),
        "round": 0,
        "streak": 0,
        "state": None,
        "cards": [],
        "claim": None,        # (rank, count)
        "won": False,
        "over": False,
    }


def make_claim(cards, rng):
    """Return (rank, count) - truthful or false, decided by a fair coin flip."""
    tell_truth = rng.random() < 0.5
    present = [card_rank(v) for v in cards]
    # Same rank-choosing rule for truthful and false claims.
    if rng.random() < 0.6:
        rank = rng.choice(present)
    else:
        rank = rng.randrange(13)
    actual = present.count(rank)
    if tell_truth:
        return rank, actual
    options = [k for k in range(4) if k != actual]
    weights = [{0: 4, 1: 4, 2: 2, 3: 1}[k] for k in options]
    return rank, rng.choices(options, weights)[0]


def claim_is_true(cards, claim):
    rank, count = claim
    return [card_rank(v) for v in cards].count(rank) == count


def start_round(game):
    """Advance to the next round: handle the 12-round reset and deal 3 cards."""
    game["round"] += 1
    position = (game["round"] - 1) % ROUNDS_PER_BLOCK
    block = (game["round"] - 1) // ROUNDS_PER_BLOCK
    a, c, seed = block_params(game, block)
    if position == 0:                 # new block -> generator restarts
        game["state"] = seed          # the seed itself is never dealt
    cards = []
    for _ in range(CARDS_PER_ROUND):
        game["state"] = lcg_next(game["state"], a, c)
        cards.append(game["state"])
    game["cards"] = cards
    game["claim"] = make_claim(cards, game["claim_rng"])


def play_choice(game, choice):
    """
    choice: 1 = Truth, 2 = Call Bluff, 3 = Pass.
    Returns a dict describing what happened. Call start_round() afterwards.
    """
    truthful = claim_is_true(game["cards"], game["claim"])
    revealed = None
    if choice == 3:
        correct = None
        game["streak"] = 0
    else:
        correct = truthful if choice == 1 else (not truthful)
        if choice == 2:
            revealed = list(game["cards"])
        game["streak"] = game["streak"] + 1 if correct else 0
    if game["streak"] >= STREAK_TO_WIN:
        game["won"] = True
        game["over"] = True
    elif MAX_ROUNDS is not None and game["round"] >= MAX_ROUNDS:
        game["over"] = True
    return {"correct": correct, "truthful": truthful, "revealed": revealed,
            "streak": game["streak"], "won": game["won"], "over": game["over"]}
