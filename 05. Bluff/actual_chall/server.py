"""
server.py - TCP front end for "Chance Is a Convenient Lie".
Run:  python3 server.py        (default port 5000, or set PORT=1234)
Play: nc localhost 5000
Standard library only. Every connection gets its own independent game.
"""

import os
import socket
import socketserver
import sys
import traceback

import challenge

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))
IDLE_TIMEOUT = 300  # seconds of silence before a connection is dropped

BANNER = """
============================================
          CHANCE IS A CONVENIENT LIE
============================================

You sit across from the dealer. Each round the
dealer deals three cards and makes a claim
about them. The dealer may be honest. Or not.

  [1] Truth       - the claim is correct
  [2] Call Bluff  - the claim is false
  [3] Pass        - skip the round (resets your streak)

Get 5 correct decisions in a row to win.
A wrong answer or a Pass resets your streak.
Call a bluff and the dealer must show the cards.
"""

MENU = """--------------------------------------------
[1] Truth
[2] Call Bluff
[3] Pass
--------------------------------------------
"""


class Handler(socketserver.StreamRequestHandler):
    def send(self, text):
        self.wfile.write(text.encode("utf-8"))
        self.wfile.flush()

    def read_choice_line(self):
        """Read one line (max 64 bytes kept). Returns None on disconnect."""
        line = self.rfile.readline(64)
        if not line:
            return None
        while not line.endswith(b"\n"):          # discard the rest of a long line
            rest = self.rfile.readline(64)
            if not rest:
                break
            line = rest
        return line.decode("utf-8", errors="ignore").strip()

    def handle(self):
        try:
            self.request.settimeout(IDLE_TIMEOUT)
            self.play()
        except (ConnectionError, socket.timeout, BrokenPipeError):
            pass
        except Exception:
            if challenge.DEBUG:
                traceback.print_exc(file=sys.stderr)
            try:
                self.send("\nThe dealer storms off. Something went wrong.\n")
            except Exception:
                pass

    def play(self):
        game = challenge.new_game()
        self.send(BANNER)
        while not game["over"]:
            challenge.start_round(game)
            cards_claim = challenge.claim_text(*game["claim"])
            self.send("\nRound %d\n\nDealer:\n\"%s\"\n\n%s" %
                      (game["round"], cards_claim, MENU))
            choice = None
            while choice is None:
                self.send("> ")
                text = self.read_choice_line()
                if text is None:
                    return
                if text in ("1", "2", "3"):
                    choice = int(text)
                else:
                    self.send("Invalid choice. Enter 1, 2, or 3.\n")
            result = challenge.play_choice(game, choice)
            self.send(self.describe(result, choice))
            if result["won"]:
                self.send("\nThe dealer slides the prize across the table:\n\n"
                          "    %s\n\nGoodbye.\n" % challenge.FLAG)
        if not result["won"]:
            self.send("\nThe dealer ends the game. Goodbye.\n")

    def describe(self, result, choice):
        out = "\n"
        if result["revealed"] is not None:
            out += "The actual cards were:\n\n"
            for v in result["revealed"]:
                out += "%s\n" % challenge.number_to_card(v)
            if result["truthful"]:
                out += "\nThe dealer was telling the TRUTH.\n"
            else:
                out += "\nThe dealer was BLUFFING.\n"
        if choice == 3:
            out += "You passed. Your streak has been reset.\n"
        elif result["correct"]:
            out += "\nCorrect!\n"
        else:
            out += "\nWrong.\n\nYour streak has been reset.\n"
        out += "\nStreak: %d/%d\n" % (result["streak"], challenge.STREAK_TO_WIN)
        return out


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server((HOST, PORT), Handler) as srv:
        print("Listening on %s:%d" % (HOST, PORT), file=sys.stderr)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
