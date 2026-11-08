#!/usr/bin/env python3
"""Regenerate the vanilla progression rows this mod must override to add subclasses.

BG3 attaches subclasses to a class through a <SubClasses> list on one progression row.
A mod can only add to that list by replacing the whole row, so this script copies the
game's FINAL version of each row (the last data layer that defines it), appends our
subclasses, and writes it into our Progressions.lsx (replacing any older copy).

Needs the game's progression files extracted into .cache/ (see tools/extract_game_data.sh).
Verifies the result and exits non-zero on any problem.
Run: python3 -I tools/gen_overrides.py
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
OURS = ROOT / "Public" / "StoneheartStorm" / "Progressions" / "Progressions.lsx"

# Game data layers, lowest priority first. The last layer defining a row wins in-game.
LAYERS = [
    CACHE / "Shared/Public/Shared/Progressions/Progressions.lsx",
    CACHE / "Shared/Public/SharedDev/Progressions/Progressions.lsx",
    CACHE / "Gustav/Public/Gustav/Progressions/Progressions.lsx",
    CACHE / "Gustav/Public/GustavDev/Progressions/Progressions.lsx",
    CACHE / "GustavX/Public/GustavX/Progressions/Progressions.lsx",
    # required dependency, loads right before this mod: DnD 5.5e All-in-One BEYOND
    CACHE / "DnD2024/Public/DnD2024_897914ef-5c96-053c-44af-0be823f895fe/Progressions/Progressions.lsx",
]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modlib import PALADIN_OATH_NAMES, uid  # noqa: E402

PALADIN_OATHS = [
    "6c4d2d14-976e-43eb-922f-320e015cb248",  # Oath of Storms
] + [uid("class:" + n) for n in PALADIN_OATH_NAMES]  # tools/gen_oaths.py
FIGHTER_ARCHETYPES = [
    "c2a6f3e4-5b1d-4f7e-9a3c-0b7d1e6f2a91",  # Boogie Woogie (Tulio)
]

# row UUID -> (description, subclass UUIDs to append). With 5.5e, oaths are chosen at Paladin level 3.
OVERRIDES = {
    "31c12f48-d62f-4e83-b475-10ed9068c9dd": ("Paladin L3 (5.5e)", PALADIN_OATHS),
    "23eacff0-9efe-4ea6-b031-19075cc96b63": ("Fighter L3 (5.5e)", FIGHTER_ARCHETYPES),
}
# rows this mod used to override (vanilla Paladin L1); removed so 5.5e's own versions apply
STALE_ROWS = {"b60618d1-c262-42b5-9fdd-2c0f7aa5e5af", "1f5396ad-65e3-4ed5-a339-d76b11af96ea"}


LIST_LAYERS = [
    CACHE / "Shared/Public/Shared/Lists/SpellLists.lsx",
    CACHE / "Shared/Public/SharedDev/Lists/SpellLists.lsx",
    CACHE / "GustavX/Public/GustavX/Lists/SpellLists.lsx",
    CACHE / "DnD2024/Public/DnD2024_897914ef-5c96-053c-44af-0be823f895fe/Lists/SpellLists.lsx",
]
OUR_LISTS = ROOT / "Public" / "StoneheartStorm" / "Lists" / "SpellLists.lsx"

# spell list UUID -> (description, spells to append). Empty with 5.5e: it ships a real Find Steed.
LIST_OVERRIDES = {}
# lists this mod used to override; removed so 5.5e's own versions apply
STALE_LISTS = {"c14c9564-1503-47a1-be19-98e77f22ff59"}  # Paladin SLevel 2 (my old Find Steed add)


def final_list(uuid):
    found, where = None, None
    for layer in LIST_LAYERS:
        if not layer.exists():
            continue
        for node in rows(ET.parse(layer)):
            if row_uuid(node) == uuid:
                found, where = node, layer
    if found is None:
        sys.exit(f"spell list {uuid} not found in any extracted game layer")
    return found, where


def spells_attr(node):
    for a in node.findall("attribute"):
        if a.get("id") == "Spells":
            return a
    sys.exit(f"spell list {row_uuid(node)} has no Spells attribute")


def do_lists():
    ours = ET.parse(OUR_LISTS)
    our_rows = rows(ours)
    for node in list(our_rows):
        if row_uuid(node) in LIST_OVERRIDES or row_uuid(node) in STALE_LISTS:
            our_rows.remove(node)
    for uuid, (desc, extra) in LIST_OVERRIDES.items():
        node, where = final_list(uuid)
        attr = spells_attr(node)
        have = [s for s in attr.get("value").split(";") if s]
        attr.set("value", ";".join(have + [s for s in extra if s not in have]))
        our_rows.append(node)
        print(f"{desc}: from {where.relative_to(CACHE)}: {len(have)} vanilla + {len(extra)} ours")
    ET.indent(ours, space="    ")
    ours.write(OUR_LISTS, encoding="UTF-8", xml_declaration=True)
    check = rows(ET.parse(OUR_LISTS))
    for uuid, (desc, extra) in LIST_OVERRIDES.items():
        hits = [n for n in check if row_uuid(n) == uuid]
        if len(hits) != 1:
            sys.exit(f"FAIL {desc}: {len(hits)} copies of list")
        vanilla = [s for s in spells_attr(final_list(uuid)[0]).get("value").split(";") if s]
        got = spells_attr(hits[0]).get("value").split(";")
        if got != vanilla + [s for s in extra if s not in vanilla]:
            sys.exit(f"FAIL {desc}: {got}")


def row_uuid(node):
    for a in node.findall("attribute"):
        if a.get("id") == "UUID":
            return a.get("value")
    return None


def rows(tree):
    return tree.getroot().find("region").find("node").find("children")


def final_row(uuid):
    found, where = None, None
    for layer in LAYERS:
        if not layer.exists():
            continue
        for node in rows(ET.parse(layer)):
            if row_uuid(node) == uuid:
                found, where = node, layer
    if found is None:
        sys.exit(f"row {uuid} not found in any extracted game layer (run tools/extract_game_data.sh)")
    return found, where


def subclass_list(node):
    sc = node.find("children/node[@id='SubClasses']/children")
    if sc is None:
        sys.exit(f"row {row_uuid(node)} has no SubClasses list")
    return sc


def main():
    ours = ET.parse(OURS)
    our_rows = rows(ours)
    for node in list(our_rows):
        if row_uuid(node) in OVERRIDES or row_uuid(node) in STALE_ROWS:
            our_rows.remove(node)
    for uuid, (desc, extra) in OVERRIDES.items():
        node, where = final_row(uuid)
        sc = subclass_list(node)
        have = [s.find("attribute").get("value") for s in sc]
        for sub in extra:
            if sub not in have:
                n = ET.SubElement(sc, "node", {"id": "SubClass"})
                ET.SubElement(n, "attribute", {"id": "Object", "type": "guid", "value": sub})
        our_rows.append(node)
        print(f"{desc}: from {where.relative_to(CACHE)}: {len(have)} vanilla + {len(extra)} ours")
    ET.indent(ours, space="    ")
    ours.write(OURS, encoding="UTF-8", xml_declaration=True)

    # verify
    check = rows(ET.parse(OURS))
    for uuid, (desc, extra) in OVERRIDES.items():
        hits = [n for n in check if row_uuid(n) == uuid]
        if len(hits) != 1:
            sys.exit(f"FAIL {desc}: {len(hits)} copies of row")
        vanilla, _ = final_row(uuid)
        want = [s.find("attribute").get("value") for s in subclass_list(vanilla)] + extra
        got = [s.find("attribute").get("value") for s in subclass_list(hits[0])]
        if sorted(set(got)) != sorted(set(want)):
            sys.exit(f"FAIL {desc}: subclasses {got} != {want}")
    do_lists()
    print("OVERRIDES_OK")


if __name__ == "__main__":
    main()
