"""Shared helpers for the StoneheartStorm generators: deterministic IDs and idempotent upserts.

Every generator writes through these helpers so re-running replaces its own entries
(matched by stats entry name / node UUID / loca contentuid) instead of duplicating them.
"""
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "Public" / "StoneheartStorm"
DATA = PUB / "Stats" / "Generated" / "Data"
LOCA = ROOT / "Localization" / "English" / "StoneheartStorm.loca.xml"
NS = uuid.UUID("3bb88991-5d00-4004-af7e-6746a0cf1c5c")  # the mod UUID

PALADIN = "ff4d9497-023c-434a-bd14-82fc367e991c"
PALADIN_OATH_NAMES = ["OathOfEternalNight", "OathOfHeresy", "OathOfRevelry", "OathOfTheSun", "OathOfWinter"]


def uid(key):
    return str(uuid.uuid5(NS, key))


def handle(key):
    return "h" + uid("loca:" + key).replace("-", "g")


ENTRY_RE = re.compile(r'new entry "([^"]+)"\n(?:(?!new entry ").*(?:\n|$))*')


def upsert_stats(fname, blocks):
    """blocks: list of stats entry texts, each starting with `new entry "Name"`."""
    p = DATA / fname
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    existing = [(m.group(1), m.group(0).strip("\n")) for m in ENTRY_RE.finditer(text)]
    new = {}
    for b in blocks:
        b = b.strip("\n")
        m = re.match(r'new entry "([^"]+)"', b)
        if not m:
            raise SystemExit(f"bad stats block: {b[:60]!r}")
        if m.group(1) in new:
            raise SystemExit(f"duplicate entry in generator: {m.group(1)}")
        new[m.group(1)] = b
    out, seen = [], set()
    for name, b in existing:
        if name in new:
            out.append(new[name])
            seen.add(name)
        else:
            out.append(b)
    out += [b for n, b in new.items() if n not in seen]
    p.write_text("\n\n".join(out) + "\n", encoding="utf-8")


def _rows(tree):
    return tree.getroot().find("region").find("node").find("children")


def _node_uuid(node):
    for a in node.findall("attribute"):
        if a.get("id") == "UUID":
            return a.get("value")
    return None


def upsert_lsx(path, node_xmls, region=None, node_id=None):
    """Replace/append nodes (matched by their UUID attribute) in a region file."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<save>\n    <version major="4" minor="7" revision="1" build="1"/>\n'
                        f'    <region id="{region}">\n        <node id="root">\n            <children>\n            </children>\n'
                        f'        </node>\n    </region>\n</save>\n', encoding="utf-8")
    tree = ET.parse(path)
    rows = _rows(tree)
    new = [ET.fromstring(x) for x in node_xmls]
    ids = {_node_uuid(n) for n in new}
    if None in ids or len(ids) != len(new):
        raise SystemExit(f"upsert_lsx {path.name}: nodes need unique UUIDs")
    for n in list(rows):
        if _node_uuid(n) in ids:
            rows.remove(n)
    for n in new:
        rows.append(n)
    ET.indent(tree, space="    ")
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def upsert_loca(entries):
    """entries: {contentuid: text}"""
    tree = ET.parse(LOCA)
    root = tree.getroot()
    for c in list(root):
        if c.get("contentuid") in entries:
            root.remove(c)
    for k, v in entries.items():
        e = ET.SubElement(root, "content", {"contentuid": k, "version": "1"})
        e.text = v
    ET.indent(tree, space="  ")
    tree.write(LOCA, encoding="utf-8", xml_declaration=True)


def attr(id_, type_, value):
    return f'<attribute id="{id_}" type="{type_}" value="{value}"/>'
