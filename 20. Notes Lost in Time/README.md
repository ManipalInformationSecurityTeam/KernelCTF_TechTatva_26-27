# Notes Lost in Time

## Jane-7710

## Forensics

## Hard

### Question Description

A forgotten recording from a legendary musician has recently resurfaced. The musician was famous for her cryptic and often nonsensical ramblings. She always claimed of getting inspiration from 15th century texts.
She pushed her instruments to their physical limits, striving for an ultra-pure divisive resonance that most people couldn't comprehend.
This particular recording sounds completely ordinary, but some secrets aren't meant to be heard and some notes and numbers have to be overlooked. 
The numbers may not be characters at all — perhaps they are merely positions.
Sometimes, you just have to look at the sound from a different perspective. Perhaps the notes or angles are telling you something.

### Hint 1
Forsake the modern American decree, and let the glyphs be weighed by their ancient birthright. The vanguard stands solitary, a single spark, while its heir follows as a pair. Count not by the machine, but by the breath of origin
### Hint 2
Let the melody fade, for it is but an illusion; the scribe’s true voice whispers only in the silent, soaring heights. Call upon Jean-Baptiste’s glass to shatter the wave and reveal the jagged peaks above. Yet, do not study the summits themselves—weigh the empty voids that stretch between them. Shrink each vast leap by a quarter of a century, but beware: the fallen figures still wear a heavy mask. To strip away the veil, your numbers must cross paths exclusively with the compounding lineage penned within the Liber Abaci. Only in this singular union will the true forms awaken, pointing your gaze straight back to the cradle of the alphabet.

#### Files to be provided

A .wav file of a peaceful music track. (UPLOAD challenge.wav ONLY)

### Intended Solution
1. Players first perform basic audio forensics such as listening to the track, checking its metadata, waveform and spectrogram.
2. The spectogram reveals certain bright spots in ultrasonic region.
3. Our encoding uses a=1,b=2 instead of normal ascii and {=27.
4. Lore hints about "ultra","notes or angles" “15th-century” concept nudge them to look past normal hearing into the high frequencies and 15th century mathematics points them towards both fourier and fibonacci.
5. Players apply a Fourier Transform (FFT) to the audio to analyse which frequencies are present. (potentially another hint pointing to fouriers can be given).
6. The FFT reveals several unnaturally strong frequency peaks that don't appear to belong to the original music.
7. They ignore the actual pitches and measure the distance (the gap) between note #1 and note #2. They see it jumped from 15,000 Hz to 15,300 Hz -> a jump of 300 Hz. ("some numbers have to be overlooked")
8. They then divide that jump by 25: 300 / 25 = 12, to recover the scrambled number.
9. They now connect back to "15th-century" and realize the key is the Fibonacci sequence.
10. They take the scrambled number (12) and XOR it with the 1st Fibonacci number (1).
11. The blender reverses itself, and they get back the original number 13 (since 12 XOR 1 = 13).
12. Finally, they look up number 13 in the custom alphabet index (a=1, b=2...), and it gives them m (first letter).
13. They repeat this for the rest of the frequencies to get the phrase m4th15c0n5t4nt and then encase it in the typical flag format to submit.

### Flag

> kernel{m4th15c0n5t4nt}
