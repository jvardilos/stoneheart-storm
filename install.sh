#!/usr/bin/env bash
# Install dist/StoneheartStorm.pak into BG3 and register it in modsettings.lsx, directly AFTER the
# required "DnD 5.5e All-in-One BEYOND" mod (this mod overrides 5.5e's Paladin/Fighter subclass rows).
# Idempotent. Backs up modsettings.lsx first. Fails loudly if the end state is wrong.
# Paths: see tools/paths.sh (override with BG3_USER=...).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/tools/paths.sh"
PAK="$HERE/dist/StoneheartStorm.pak"
MODS="$BG3_USER/Mods"
SETTINGS="$BG3_USER/PlayerProfiles/Public/modsettings.lsx"
UUID="3bb88991-5d00-4004-af7e-6746a0cf1c5c"

[ -s "$PAK" ] || { echo "Build first: $HERE/build.sh"; exit 1; }
[ -f "$SETTINGS" ] || { echo "modsettings.lsx not found: $SETTINGS (set BG3_USER)"; exit 1; }
[ -n "$(dnd55_pak)" ] || { echo "Required mod missing: install 'DnD 5.5e All-in-One BEYOND' into $MODS first"; exit 1; }

if command -v tasklist >/dev/null 2>&1; then
  tasklist 2>/dev/null | grep -qi "bg3" && { echo "Quit Baldur's Gate 3 first (it rewrites modsettings.lsx on exit)."; exit 1; } || true
else
  pgrep -f "Baldur's Gate 3|bg3(_dx11)?(\.exe)?$" >/dev/null && { echo "Quit Baldur's Gate 3 first (it rewrites modsettings.lsx on exit)."; exit 1; } || true
fi

# Check the dependency is enabled BEFORE changing anything on disk.
python3 -I - "$SETTINGS" "$DND55_UUID" <<'PY'
import sys
import xml.etree.ElementTree as ET
path, dep = sys.argv[1:3]
ids = [a.get("value") for a in ET.parse(path).getroot().iter("attribute") if a.get("id") == "UUID"]
if dep not in ids:
    sys.exit("5.5e mod is installed but not enabled in modsettings.lsx: enable 'DnD 5.5e All-in-One BEYOND' (e.g. in the game's mod manager) and re-run")
PY

cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"
mkdir -p "$MODS"
cp "$PAK" "$MODS/StoneheartStorm.pak"

python3 -I - "$SETTINGS" "$UUID" "$DND55_UUID" <<'PY'
import sys
import xml.etree.ElementTree as ET
path, ours, dep = sys.argv[1:4]
tree = ET.parse(path)
mods = next(n for n in tree.getroot().iter("node") if n.get("id") == "Mods").find("children")
def uid(n): return next((a.get("value") for a in n.findall("attribute") if a.get("id") == "UUID"), None)
entries = list(mods)
dep_node = next((n for n in entries if uid(n) == dep), None)
if dep_node is None:
    sys.exit("5.5e mod is installed but not enabled in modsettings.lsx: enable 'DnD 5.5e All-in-One BEYOND' (e.g. in the game's mod manager) and re-run")
for n in entries:
    if uid(n) == ours:
        mods.remove(n)
node = ET.Element("node", {"id": "ModuleShortDesc"})
for i, t, v in [("Folder", "LSString", "StoneheartStorm"), ("MD5", "LSString", ""), ("Name", "LSString", "Stoneheart Storm"),
                ("PublishHandle", "uint64", "0"), ("UUID", "guid", ours), ("Version64", "int64", "36028797018963968")]:
    ET.SubElement(node, "attribute", {"id": i, "type": t, "value": v})
mods.insert(list(mods).index(dep_node) + 1, node)
ET.indent(tree, space="    ")
tree.write(path, encoding="UTF-8", xml_declaration=True)
order = [uid(n) for n in mods]
assert order.count(ours) == 1 and order.index(ours) == order.index(dep) + 1, "load order check failed"
print(f"registered at load position {order.index(ours) + 1} of {len(order)}, directly after 5.5e")
PY

[ -s "$MODS/StoneheartStorm.pak" ] || { echo "pak missing after copy"; exit 1; }
echo "INSTALL_OK"
