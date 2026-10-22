# The Wind Remembers
## Author
yam1_
## Domain
Reverse Engg
## Difficulty
Easy

## Description
An ancient scroll reads: “THE WIND REMEMBERS. Eight paths sleep beneath
the rain. Carry the flame. Follow what it reveals.” Explore the supplied
game build, uncover what its wind trials remember, and recover the flag.

## Solution
**Step 1: Restore the inventory**

The game starts with its inventory disabled. Pressing **I** displays “Inventory unavailable.” The gate is initialized in the native library. Extract a fresh release ZIP, then open `libtrial.so` (Linux) or `libtrial.dll` (Windows) in Ghidra.

| Build | Ghidra file offset | Original bytes | Patched bytes |
| --- | --- | --- | --- |
| Linux | `0x2EF0` | `48 C7 07 00 00 00 00` | `48 C7 07 01 00 00 00` |
| Windows | `0x7C0` | `48 C7 01 00 00 00 00` | `48 C7 01 01 00 00 00` |

This changes the native state initializer from zero to one, setting the inventory gate while leaving the remaining progression state unset. In Ghidra, go to the file offset, right-click the instruction, and choose **Patch Instruction** to change its immediate value from `0` to `1`. Export with format **Original File** and enable **Export User Byte Modifications**. The **Ghidra Zip File** export format is for a Ghidra project archive; it is not a replacement game library. Replace the corresponding library beside the game executable with the exported file, restart the game, and press **I**.

**Step 2: Unlock and complete the eight trials**

Open the **Ancient Scroll** in the inventory to unlock the Wind Trials menu. Select one wind, start its trial, and follow the **torch smoke** at walking speed. Approach its chest and press **E**. Repeat for all eight winds.

| Wind | Recovered fragment |
| --- | --- |
| Northwest | “The sword” |
| North | “sleeps where” |
| Northeast | “three winds” |
| East | “agree.” |
| Southeast | “Let the North” |
| South | “embrace the East,” |
| Southwest | “while the West” |
| West | “walks beside them.” |

Press **J** to read the recovered clues. In order, they form:

> The sword sleeps where three winds agree.  
> Let the North embrace the East,  
> while the West walks beside them.

**Step 3: Follow the joined wind**

The message indicates **North + East + West**. Once all eight clues are collected, open **I → Wind Trials**, select exactly those three winds, and press **START TRIAL**.

The final smoke direction comes from the position-dependent native wind fields:

```text
direction = normalize(V_N(position) + V_E(position) + V_W(position))
```

Follow the changing smoke through the final route. Other three-wind selections also produce combined vectors, but they do not satisfy the final sword validation.

**Step 4: Awaken the sword**

After the joined route reaches the final clearing, the stone reveals the sword’s hilt. Approach and press **E** at the **INSPECT** prompt. The cinematic plays: the stone breaks and the sword rises. The native core validates the route and releases the flag only after the sequence finishes.

## Flag
**Flag:** `kernel{z3ld4_1s_w4it1ng}`
