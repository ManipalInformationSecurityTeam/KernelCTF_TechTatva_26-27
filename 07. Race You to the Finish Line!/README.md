# Race You to the Finish Line\!

## Author
DeliverHellVeil

## Domain
OSINT

## Difficulty
Medium

### Question Description

Extract the 11, and smash that like button\!

The challenge provides eleven lines, each containing six words. Decode the lines to uncover a YouTube video, investigate its contents, and follow the clues to discover the final flag.

**Instagram Handle Hint:**

`[First word of the group] + [Last word of the track] + [When it arrives]`

**Format:** `@word_word_number`

Eleven lines unlock the gate; six words inside each verse.

### Intended Solution

**Step 1: Decode the Base64**

The challenge provides eleven lines, each containing six words. The hint, “Eleven lines unlock the gate; six words inside each verse,” indicates that each line should be converted into a six-bit binary number.

Classify each word as positive (`1`) or negative (`0`):

- Positive words = `1`
- Negative words = `0`

Applying this rule to each line produces the following binary groups:

| Line | Binary |
| --- | --- |
| Life breaks; light heals, hope shines. | `101111` |
| Death kills; rot destroys dark joy. | `000001` |
| Hate ruins; fear crushes dead ash. | `000000` |
| Love weeps; pain mends, peace blooms. | `100111` |
| Joy fades; builders build ruined graves. | `101100` |
| Pain heals; light saves sweet decay. | `011110` |
| Truth wins; love suffers grim death. | `111000` |
| Light grows; warmth saves freezing life. | `111101` |
| Hate creates foul rot, heroes die. | `010010` |
| Hope fails; builders save bright ruins. | `101110` |
| Love wins; truth kills vile liars. | `111000` |

Combining the eleven six-bit groups gives:

```
101111 000001 000000 100111 101100 011110
111000 111101 010010 101110 111000
```

Each six-bit group corresponds to a Base64 character. Converting the groups using the standard Base64 alphabet produces the decoded string:

```
vBAnse49Su4
```

**Step 2: Find the YouTube Video**

The clue **“smash that like button”** points to YouTube. Use the decoded string as the video ID to access the video:

[https://www.youtube.com/watch?v=vBAnse49Su4](<https://www.youtube.com/watch?v=vBAnse49Su4>)

The challenge title, **“Race You to the Finish Line\!”**, suggests examining the end of the video or its tracklist for the next clue.

**Step 3: Identify the Finnish Band and Track**

Investigating the video's tracklist reveals a Finnish band and a relevant track:

- Artist: Scarlet Youth
- Track: Gleaming Endless Ocean
- Country: Finland
- Timestamp: 36:38

The Instagram hint instructs us to combine the first word of the group, the last word of the track, and the time when it arrives, using the format `@word_word_number`.

Applying these clues:

- First word of the group: `scarlet`
- Last word of the track: `ocean`
- Timestamp: `3638`

Combining the three components produces the Instagram handle:

```
@scarlet_ocean_3638
```

**Step 4: Retrieve the Flag**

Use the Instagram handle as the next lead in the challenge. Following it leads to a Pastebin link containing the flag.

The recovered flag is:

### Flag

> `kernel{g3t_l0st_in_th3_w4ll_0f_gu1t4rs}`