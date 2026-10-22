#!/usr/bin/env python3
"""Toggle the inventory unlock in this loose Linux test build only."""

from pathlib import Path
import subprocess
import sys
import zipfile


HERE = Path(__file__).resolve().parent
LIBRARY = HERE / "libtrial.so"
RELEASE_ZIP = HERE / "Zip" / "TheWindRemembers-Linux-x86_64.zip"
ZIP_MEMBER = "master-sword-trial/libtrial.so"
INITIALIZER = bytes.fromhex("48 c7 07 00 00 00 00 c3")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off", "status", "play"):
        raise SystemExit("Usage: ./test_inventory_cheat.py on|off|status|play")

    with zipfile.ZipFile(RELEASE_ZIP) as archive:
        original = archive.read(ZIP_MEMBER)
    if original.count(INITIALIZER) != 1:
        raise SystemExit("The release library does not match this test patch.")
    patch_offset = original.index(INITIALIZER) + 3

    patched = bytearray(original)
    patched[patch_offset] = 1
    current = LIBRARY.read_bytes()
    if current != original and current != patched:
        raise SystemExit("libtrial.so differs from both known versions; refusing to overwrite it.")

    command = sys.argv[1]
    if command == "status":
        print("Inventory cheat is ON." if current == patched else "Inventory cheat is OFF.")
        return
    if command == "off":
        if current != original:
            LIBRARY.write_bytes(original)
        print("Inventory cheat is OFF. Restart the game to apply it.")
        return
    if current != patched:
        LIBRARY.write_bytes(patched)
    print("Inventory cheat is ON. Press I in game to open inventory.")
    if command == "play":
        subprocess.run([str(HERE / "game.x86_64")], cwd=HERE, check=True)


if __name__ == "__main__":
    main()
