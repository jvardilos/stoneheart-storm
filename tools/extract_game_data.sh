#!/usr/bin/env bash
# Extract the slices of BG3's data (and of the required 5.5e mod) this mod is built against into .cache/.
# Read-only reference for the generators and tools/check_refs.py. Re-run after a game or 5.5e update,
# then re-run tools/gen_overrides.py.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
source "$HERE/tools/paths.sh"
DV="$HERE/tools/divine/Divine.dll"
C="$HERE/.cache"
[ -f "$DV" ] || { echo "run tools/setup_divine.sh first"; exit 1; }
[ -f "$BG3_DATA/Shared.pak" ] || { echo "BG3 data not found at: $BG3_DATA (set BG3_DATA)"; exit 1; }

x() { dotnet "$DV" -g bg3 -a extract-package -s "$1" -d "$C/$2" -x "$3" >/dev/null; }

for layer in Shared SharedDev; do
  for p in "Stats/Generated/Data/*" "ClassDescriptions/*" "Progressions/*" "Lists/*" "ActionResourceDefinitions/*"; do
    x "$BG3_DATA/Shared.pak" Shared "Public/$layer/$p"
  done
done
for layer in Gustav GustavDev; do
  for p in "Progressions/Progressions.lsx" "Stats/Generated/Data/*" "Stats/Generated/TreasureTable.txt"; do
    x "$BG3_DATA/Gustav.pak" Gustav "Public/$layer/$p"
  done
done
x "$BG3_DATA/GustavX.pak" GustavX "Public/GustavX/*"

# Required dependency: DnD 5.5e All-in-One BEYOND (the final data layer this mod builds on).
P55="$(dnd55_pak)"
[ -n "$P55" ] || { echo "5.5e mod not found in $BG3_USER/Mods (install 'DnD 5.5e All-in-One BEYOND' first)"; exit 1; }
for p in "Progressions/*" "ClassDescriptions/*" "Lists/*" "Stats/Generated/Data/*"; do
  x "$P55" DnD2024 "Public/DnD2024_$DND55_UUID/$p"
done

for f in Shared/Public/SharedDev/Progressions/Progressions.lsx GustavX/Public/GustavX/Progressions/Progressions.lsx \
         Gustav/Public/GustavDev/Stats/Generated/Data/Weapon.txt \
         "DnD2024/Public/DnD2024_$DND55_UUID/Progressions/Progressions.lsx"; do
  [ -s "$C/$f" ] || { echo "MISSING: $f"; exit 1; }
done
echo "EXTRACT_OK"
