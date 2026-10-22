# Antwerp slip up

## Jane-7710

## Forensics

## Medium

### Question Description

Antwerp, 03:14 CET. A high-security diamond vault has been robbed without triggering a single alarm.
The only lead we could recover is two corrupted CCTV footages. The two cameras were filming the main vault from two slightly different frames. The camera didn't just fail, its recordings were mathematically scrambled and reversed in every way. Both recordings abruptly terminated at the same time.
Somewhere in those broken frames is the clue that could explain how the heist was carried out.

### Hint 1:
Ask the vessel its moment of birth, but read the clock in reverse. Then plunge to the absolute floor of the data. The mirrored dawn gives the numbers. The abyss gives the math.

#### Files

2 cctv video files

### Intended Solution


1. Players get handed two corrupted CCTV mp4s from the vault. On inspection, both videos just look like scrambled static bs.
2. The Metadata & The Hex: Going off the hint ("Ask the vessel its moment of birth..."), they run exiftool on the files. Instead of a normal creation time, they spot a weird comment tag: pastebin[.]com / 53 46 73 46 4a 42 68 4a. They realize it's a defanged hex string. Converting the hex gives the Pastebin ID SFsFJBhJ.
3. Hitting that Pastebin link gives them the text: "The vessel remembers its birth. 10:42:09".
4. They dive to the absolute bottom of the file (EOF). Running strings reveals fake system crash dumps (--- SYS_CRASH_DUMP_0x4F ---). Instead of Base64, it's an ASCII art visual math grid built with dots to completely break ChatGPT's tokenization.
5. Reading the ASCII grid themselves gives the actual equation used to scramble the scanlines:
shift = -1 * ( (Y*Y // DIVISOR) + (DRIFT * frame) + (Y % MODULO) )
6. So Video 1 holds the even rows shifting left (-1), and Video 2 holds the odd rows shifting right (+1). But the variables are missing.
7. The original hint told them to "read the clock in reverse." They take that 10:42:09 timestamp from the Pastebin, flip that shit to 09, 42, 10, and plug it into the math:
DIVISOR = 9
DRIFT = 42
MODULO = 10
8. Now they just gotta write a quick Python script to reverse allat. Plug those constants in, undo the shifts, and zipper the even rows from Cam 1 with the odd rows from Cam 2 back together to rebuild the frames.
9. The footage stitches back perfectly, playing the analog horror heist video. The flag pops up right around the 20-second mark.
   
### Flag

> kernel{g3t_b3tt34_cctv_l0l}
