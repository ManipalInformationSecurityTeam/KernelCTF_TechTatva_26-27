# Tom Riddle's Invisible Ink

## Author
TouchReality

## Domain
Cryptography

## Difficulty
Easy

## Description
Here's what's given to the players:
- Challenge Description: Deep beneath Hogwarts, you discover a torn page from Tom Riddle’s diary. Thirty symbols appear beneath a sketch of six pillars. As the ink dries, a message appears:
“The serpent began at the upper left. At every wall, it descended and turned back."

hint: A final note reads:
“Discard the capital Xs that fill the empty stones.”

Works on the principle of a spiral cipher but slightly modified. When you rewrite the given flag in columns of 6 (hint-6 pillars) from top to bottom, you have a matrix that looks something like this. Now, we move from left to right on the top row, move down and the move right to left and continue the process (shaped like a coiled up snake instead of spiral).

<img width="110" height="112" alt="Screenshot 2026-10-21 at 11 36 50 PM" src="https://github.com/user-attachments/assets/c1ee65ad-5c75-4fb8-8f14-25d850437bd9" />

## Flag
kernel{basilisk_is_a_snake?}



