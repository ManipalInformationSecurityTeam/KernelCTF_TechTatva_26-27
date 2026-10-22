"""
Seeds castle.db with:

  - characters:    the table the (vulnerable) people-search endpoint
                    queries directly. Hermione Granger has a real row
                    here with visible=0 -- she exists, but is filtered
                    out of normal results.
  - map_services:  internal infrastructure recon data (hostname/port
                    of the internal service). Reachable only via
                    UNION-based SQL injection, never through normal
                    search results.
  - map_notes:     an archived note containing the phrase needed to
                    unlock the internal service's Room of Requirement.
                    Also reachable only via UNION-based SQL injection.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "castle.db")

# (name, house, note, visible)
CHARACTERS = [
    ("Harry Potter", "Gryffindor", "Currently loitering near the Great Hall.", 1),
    ("Ron Weasley", "Gryffindor", "Has mysteriously vanished near the kitchens. Investigate the biscuits.", 1),
    ("Fred Weasley", "Gryffindor", "Location unclear. Possibly also two locations at once.", 1),
    ("George Weasley", "Gryffindor", "See: Fred Weasley. Do not attempt to tell them apart.", 1),
    ("Ginny Weasley", "Gryffindor", "In the library, several books deep.", 1),
    ("Neville Longbottom", "Gryffindor", "Has lost something. Again.", 1),
    ("Luna Lovegood", "Ravenclaw", "Facing the wrong way on purpose.", 1),
    ("Draco Malfoy", "Slytherin", "Sulking ornamentally outside the dungeons.", 1),
    ("Severus Snape", "Slytherin", "Circling the dungeons like a bad smell that took offence.", 1),
    ("Albus Dumbledore", "Staff", "Somewhere he shouldn't need to explain himself.", 1),
    ("Minerva McGonagall", "Staff", "Patrolling with the precise fury of a woman who has seen everything.", 1),
    ("Remus Lupin", "Staff", "Pacing. Checking the moon. Pacing again.", 1),
    ("Sirius Black", "Marauder", "Technically not supposed to be here at all.", 1),
    ("James Potter", "Marauder", "A memory, mostly. The map remembers him anyway.", 1),
    ("Peter Pettigrew", "Marauder", "Hard to find. Deliberately.", 1),
    # Hermione: a real row, deliberately filtered out of normal results.
    ("Hermione Granger", "Gryffindor",
     "Dot suppressed at the charm-work level on someone's instruction. "
     "She is in the castle. The map is simply not allowed to say where.", 0),
]

MAP_SERVICES = [
    # (hostname, port, note)
    ("map-internal", 5001,
     "Internal castle infrastructure node. Not reachable from outside "
     "the grounds -- or shouldn't be."),
]

MAP_NOTES = [
    ("Found folded into the back of Filch's ledger: an old charm-note. "
     "Whoever next needs the Room of Requirement's archive should simply "
     "say, to the wall: mischief managed. It has always worked before."),
]


def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            house TEXT NOT NULL,
            note TEXT NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1
        )
    """)
    cur.executemany(
        "INSERT INTO characters (name, house, note, visible) VALUES (?, ?, ?, ?)",
        CHARACTERS,
    )

    cur.execute("""
        CREATE TABLE map_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            port INTEGER NOT NULL,
            note TEXT NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO map_services (hostname, port, note) VALUES (?, ?, ?)",
        MAP_SERVICES,
    )

    cur.execute("""
        CREATE TABLE map_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO map_notes (content) VALUES (?)",
        [(n,) for n in MAP_NOTES],
    )

    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH}")


if __name__ == "__main__":
    seed()
