#!/usr/bin/env python3
"""Static reference check: every spell/status/passive/interrupt/icon the mod references must be
defined by the mod or by vanilla (.cache). Exits non-zero and lists dangling references.
Run: python3 -I tools/check_refs.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "Public" / "StoneheartStorm"
CACHE = ROOT / ".cache"

ENTRY = re.compile(r'^new entry "([^"]+)"', re.M)


def defined(paths):
    names, icons = set(), set()
    for p in paths:
        t = p.read_text(encoding="utf-8", errors="ignore")
        names.update(ENTRY.findall(t))
        icons.update(re.findall(r'data "Icon" "([^"]+)"', t))
    return names, icons


ours = sorted((PUB / "Stats" / "Generated" / "Data").glob("*.txt"))
vanilla = [p for p in CACHE.rglob("*.txt") if "Stats" in p.parts]
if not vanilla:
    sys.exit("no vanilla stats in .cache (run tools/extract_game_data.sh)")
our_names, our_icons = defined(ours)
van_names, van_icons = defined(vanilla)
known = our_names | van_names

# status names may also be vanilla engine statuses not in stats files; allow a small list
ENGINE_STATUSES = {"PRONE", "SG_Prone", "SG_Restrained", "SG_Incapacitated", "SG_Polymorph", "SG_Blinded",
                   "SG_Charmed", "SG_Frightened", "SG_Poisoned", "SG_Paralyzed", "SG_Grappled", "SURPRISED"}

refs = []  # (file, kind, name)
for p in ours:
    t = p.read_text(encoding="utf-8")
    for kind, pat in [
        ("spell", r'UnlockSpell\(([A-Za-z0-9_]+)\)'),
        ("interrupt", r'UnlockInterrupt\(([A-Za-z0-9_]+)\)'),
        ("using", r'^using "([^"]+)"'),
        ("spell", r'UseSpell\([A-Z]+,([A-Za-z0-9_]+)'),
        ("status", r'ApplyStatus\((?:SELF,|SWAP,|OBSERVER_(?:OBSERVER|TARGET|SOURCE),)?([A-Za-z0-9_.]+),'),
        ("status", r'ApplyStatus\(([A-Za-z0-9_]+)\)'),
        ("status", r"HasStatus\('([A-Za-z0-9_]+)'"),
        ("passive", r"HasPassive\('([A-Za-z0-9_]+)'"),
        ("passive", r'data "PassivesOnEquip" "([^"]+)"'),
        ("spell", r'data "ContainerSpells" "([^"]+)"'),
        ("spell", r'data "RootSpellID" "([^"]+)"'),
    ]:
        for m in re.finditer(pat, t, re.M):
            for name in m.group(1).split(";"):
                if name:
                    refs.append((p.name, kind, name))
    for icon in re.findall(r'data "Icon" "([^"]+)"', t):
        if icon not in van_icons:
            refs.append((p.name, "icon", icon))

for lsx in [PUB / "Progressions" / "Progressions.lsx", PUB / "Lists" / "PassiveLists.lsx"]:
    t = lsx.read_text(encoding="utf-8")
    for v in re.findall(r'id="(?:PassivesAdded|Passives)" type="LSString" value="([^"]*)"', t):
        for name in re.split(r"[;,]", v):
            if name:
                refs.append((lsx.name, "passive", name))
t = (PUB / "Lists" / "SpellLists.lsx").read_text(encoding="utf-8")
for v in re.findall(r'id="Spells" type="LSString" value="([^"]*)"', t):
    for name in v.split(";"):
        if name:
            refs.append(("SpellLists.lsx", "spell", name))

bad = sorted({r for r in refs if r[1] == "icon" or (r[2] not in known and r[2] not in ENGINE_STATUSES)})
for f, kind, name in bad:
    print(f"DANGLING {kind}: {name}  (in {f})")
if bad:
    sys.exit(1)
print(f"REFS_OK {len(refs)} references checked")
