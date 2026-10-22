# Bluff 
## cipher_muse777
## Crypto

## Easy

## Question Description 
The dealer smiles. The cards are dealt. The claims grow bolder with every round, but luck has a peculiar habit of repeating itself. Trust your instincts, question the table, and remember: the house isn't the only one allowed to bluff.

### Intended solution
- The player connects to the challenge server and starts playing the card game.
- Each round, the dealer reveals 3 cards and makes a claim such as: I have 2 Queens.
- The player initially does not know whether the claim is true or false.
- Calling Bluff reveals the three cards from that round, giving the player information about the underlying card sequence.
- The player converts the cards into their numerical values:
A♠ = 0
2♠ = 1
...
K♠ = 12
A♥ = 13
...
K♣ = 51
- After collecting several revealed cards, the player notices that the values are not truly random.
- The sequence follows a Linear Congruential Generator:
```
x{n+1}=(ax{n}+c) mod 52 
```
- Consecutive revealed cards therefore satisfy:
```
x1=(ax0+c) mod 52 
x2=(ax1+c) mod 52
```
- Subtracting the equations eliminates (c):

```
x2-x1\=a(x1-x0) mod 52
```
- The challenge uses a small predefined set of possible values for (a), so the player can test the possible values against the observed sequence.
- Once (a) is recovered, (c) can be calculated using:
```
c=x_1-ax_0 mod 52
```
- The player verifies the recovered (a) and (c) against additional revealed cards.
- Once (a), (c), and the current generator state are known, future cards can be predicted.
For example:
```
x{next}=(ax+c) mod52 
```
- Applying this repeatedly produces the future card values.
- The numerical values are converted back into cards using:
```
rank=x mod13
suit=x/13 (take whole num)
```
- This allows the player to know the exact three cards that will appear in future rounds.
- The player compares the predicted cards with the dealer's claim.
- The player does not need to predict whether the dealer is generally truthful or dishonest. They only need to determine whether the current claim matches the predicted cards.
- The generator does not continue indefinitely with the same parameters.
- Every 12 rounds, a new set of parameters is generated and the generator is restarted.
- Therefore, the player treats the game as separate blocks:
Rounds 1–12
Rounds 13–24
Rounds 25–36
...
- The player must recover the parameters again when a new block begins.
- Every correct Truth or Call Bluff increases the player's streak.
- A wrong answer resets the streak.
- Passing also resets the streak.
- The player needs 5 consecutive correct decisions.
- Once the streak reaches 5, the challenge is completed and the flag is revealed.

### Flag 
kernel{ch4nc3_1s_4_c0nv3n13nt_l13}

