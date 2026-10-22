# A Message Misread

## cipher_muse777

## Crypto

## Easy

### Question Description
Beyond the valley, two images mark the path up a forgotten HILL. Each carries traces of a message left behind by someone who never reached the summit. The path is not as straightforward as it seems, and the truth may look different depending on which way you climb. Find the message hidden along the way, and discover what waits at the top.

### Intended Solution 
- the key is given in the question HILL
- The player is given 2 images that looks ordinary at first. The main goal is to figure out whether the image contains information hidden inside it.
- By inspecting the image carefully and noticing the repeated patterns/details, the player realizes that certain parts of the image are
- intentionally different.
- These differences are used to extract a sequence of binary values (0 and 1).
- The extracted bits are grouped into 8-bit bytes. At this point, the result does not look like normal ASCII text, which suggests that
- another encoding is being used.
- In the comments of the file we can subtly hint baudot code so they understand they must group it as 5- bit 
- The bytes are then treated as one continuous binary stream and regrouped into 5-bit chunks.
- These 5-bit values correspond to ITA2 (International Telegraph Alphabet No. 2), commonly known as Baudot code.
- Decoding the 5-bit groups using ITA2 produces a string of letters. This string is the ciphertext for the next stage.
- The player then recognizes that the ciphertext was encrypted using a Hill cipher.
- The key matrix is obtained from the other clue/artifact provided with the challenge.
- Using the key matrix (K), the player calculates its inverse modulo 26:
```
P=K^-1 C mod(26)
```
- The decrypted result gives the plaintext message and ultimately reveals the first half of the flag.
- now since the second image is like the negative of our first image, we get the lsb and reverse the order and then do the above process to get the second half of the flag 

### Flag
kernel{d1d_y0u_r3ally_th1nk_1t_w4s_th3_s4m3}
