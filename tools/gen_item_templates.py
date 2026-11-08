#!/usr/bin/env python3
"""Generate one child root template per custom item so the item is created with OUR stat
(and name), while borrowing the parent template's model.

Also rewrites each item's `RootTemplate` line in Weapon.txt / Armor.txt to the generated GUID.
Verifies its end state and exits non-zero on any mismatch. Run: python3 -I tools/gen_item_templates.py
"""
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "Public" / "StoneheartStorm"
OUT = PUB / "RootTemplates" / "SSTORM_Items.lsx"
NS = uuid.UUID("3bb88991-5d00-4004-af7e-6746a0cf1c5c")  # the mod UUID

# (stat name, parent template GUID, name handle, description handle, stat file)
ITEMS = [
    ("SSTORM_WPN_AssassinsBlade", "467ddb4f-6791-41fa-99f7-ee8620d63bbe", "hSSTORMwpnassassinNAME", "hSSTORMwpnassassinDESC", "Weapon.txt"),
    ("SSTORM_WPN_BastardSword", "1865323f-b428-4791-a0a9-578841e57463", "hSSTORMwpnbastardNAME", "hSSTORMwpnbastardDESC", "Weapon.txt"),
    ("SSTORM_WPN_ElvenFoil", "7061f489-4b13-4982-aa09-cf0ad961e75f", "hSSTORMwpnfoilNAME", "hSSTORMwpnfoilDESC", "Weapon.txt"),
    ("SSTORM_WPN_HookSword", "d60524f4-583e-4b16-91b2-871221d441cf", "hSSTORMwpnhookNAME", "hSSTORMwpnhookDESC", "Weapon.txt"),
    ("SSTORM_WPN_ParryingDagger", "569b0f3d-abcd-4b01-aaf0-979091288163", "hSSTORMwpnparryNAME", "hSSTORMwpnparryDESC", "Weapon.txt"),
    ("SSTORM_WPN_Dervish", "868217db-9dcb-414c-bb88-e321ab3e0349", "hSSTORMwpndervishNAME", "hSSTORMwpndervishDESC", "Weapon.txt"),
    ("SSTORM_WPN_Zweihander", "ecfb9f69-5bc3-402e-acd8-c91d57e28403", "hSSTORMwpnzweiNAME", "hSSTORMwpnzweiDESC", "Weapon.txt"),
    ("SSTORM_WPN_VindrScimitar", "d60524f4-583e-4b16-91b2-871221d441cf", "hSSTORMwpnvindrNAME", "hSSTORMwpnvindrDESC", "Weapon.txt"),
    ("SSTORM_WPN_MountainCleaver", "58925ad8-f9da-482c-82da-70bede9bf2b8", "hSSTORMwpncleaverNAME", "hSSTORMwpncleaverDESC", "Weapon.txt"),
    ("SSTORM_WPN_PortableBallista", "45d888b5-e002-4bb8-85d7-6df569aceaa4", "hSSTORMwpnballistaNAME", "hSSTORMwpnballistaDESC", "Weapon.txt"),
    ("SSTORM_ARM_Brigandine_Body", "02ae5d88-8044-43df-8363-02a2900776db", "hSSTORMarmbrigNAME", "hSSTORMarmbrigDESC", "Armor.txt"),
    ("SSTORM_ARM_BandedPlate_Body", "34a71679-0ab5-4fd4-bba8-d6ad341ee490", "hSSTORMarmbandedNAME", "hSSTORMarmbandedDESC", "Armor.txt"),
    ("SSTORM_ARM_HeroPlate_Body", "34a71679-0ab5-4fd4-bba8-d6ad341ee490", "hSSTORMarmheroNAME", "hSSTORMarmheroDESC", "Armor.txt"),
    ("SSTORM_ARM_Lamellar_Body", "8ed82f7e-fdd4-4a9f-94b6-f256c599bfdd", "hSSTORMarmlamellarNAME", "hSSTORMarmlamellarDESC", "Armor.txt"),
    ("SSTORM_ARM_MountainPlate_Body", "5427c806-5565-421f-a00f-a8282a9f504f", "hSSTORMarmmountainNAME", "hSSTORMarmmountainDESC", "Armor.txt"),
    ("SSTORM_ARM_ReverberatingShield", "53b3317f-5a52-41c0-89ea-c6ef31adc4f7", "hSSTORMarmreverbNAME", "hSSTORMarmreverbDESC", "Armor.txt"),
]


def guid_for(stat):
    return str(uuid.uuid5(NS, "item:" + stat))


def build_lsx():
    nodes = []
    for stat, parent, nh, dh, _ in ITEMS:
        nodes.append(f'''				<node id="GameObjects">
					<attribute id="Description" type="TranslatedString" handle="{dh}" version="1" />
					<attribute id="DisplayName" type="TranslatedString" handle="{nh}" version="1" />
					<attribute id="LevelName" type="FixedString" value="" />
					<attribute id="MapKey" type="FixedString" value="{guid_for(stat)}" />
					<attribute id="Name" type="LSString" value="{stat}_Template" />
					<attribute id="ParentTemplateId" type="FixedString" value="{parent}" />
					<attribute id="Stats" type="FixedString" value="{stat}" />
					<attribute id="Type" type="FixedString" value="item" />
				</node>''')
    return ('<?xml version="1.0" encoding="utf-8"?>\n<save>\n'
            '\t<version major="4" minor="0" revision="9" build="0" lslib_meta="v1,bswap_guids" />\n'
            '\t<region id="Templates">\n\t\t<node id="Templates">\n\t\t\t<children>\n'
            + "\n".join(nodes) +
            '\n\t\t\t</children>\n\t\t</node>\n\t</region>\n</save>\n')


def patch_stat(text, stat, guid):
    m = re.search(r'new entry "%s"\n(?:(?!new entry).*\n?)*' % re.escape(stat), text)
    if not m:
        raise SystemExit(f"stat entry not found: {stat}")
    blk = m.group(0)
    if re.search(r'^data "RootTemplate" ', blk, re.M):
        new = re.sub(r'^data "RootTemplate" "[^"]*"', f'data "RootTemplate" "{guid}"', blk, flags=re.M)
    else:
        new = re.sub(r'^(using "[^"]*"\n)', r'\1' + f'data "RootTemplate" "{guid}"\n', blk, count=1, flags=re.M)
    return text.replace(blk, new, 1)


def main():
    OUT.write_text(build_lsx(), encoding="utf-8")
    files = {}
    for stat, _, _, _, fname in ITEMS:
        p = PUB / "Stats" / "Generated" / "Data" / fname
        files.setdefault(p, p.read_text(encoding="utf-8"))
        files[p] = patch_stat(files[p], stat, guid_for(stat))
    for p, t in files.items():
        p.write_text(t, encoding="utf-8")
    # verify end state
    for stat, parent, _, _, fname in ITEMS:
        t = (PUB / "Stats" / "Generated" / "Data" / fname).read_text(encoding="utf-8")
        m = re.search(r'new entry "%s"\n(?:(?!new entry).*\n?)*' % re.escape(stat), t)
        rts = re.findall(r'^data "RootTemplate" "([^"]*)"', m.group(0), re.M)
        if rts != [guid_for(stat)]:
            sys.exit(f"FAIL {stat}: RootTemplate lines {rts}")
    lsx = OUT.read_text(encoding="utf-8")
    for stat, parent, *_ in ITEMS:
        if lsx.count(f'value="{guid_for(stat)}"') != 1 or f'value="{parent}"' not in lsx:
            sys.exit(f"FAIL template missing for {stat}")
    print(f"GEN_OK {len(ITEMS)} item templates")


if __name__ == "__main__":
    main()
