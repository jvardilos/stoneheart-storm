#!/usr/bin/env bash
# Build dist/StoneheartStorm.pak with the ported divine (tools/setup_divine.sh). Fails loudly on any step.
# Runs the reference check when the game-data cache exists (tools/extract_game_data.sh).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DIVINE="${DIVINE:-$HERE/tools/divine/Divine.dll}"
STAGE="$HERE/.stage"
OUT="$HERE/dist/StoneheartStorm.pak"

[ -f "$DIVINE" ] || { echo "divine not found at $DIVINE (run tools/setup_divine.sh)"; exit 1; }
if [ -d "$HERE/.cache" ]; then
  python3 -I "$HERE/tools/check_refs.py"
else
  echo "WARNING: no .cache/ (run tools/extract_game_data.sh) - skipping the reference check"
fi

rm -rf "$STAGE" && mkdir -p "$STAGE" "$HERE/dist"
cp -R "$HERE/Mods" "$HERE/Public" "$STAGE/"
mkdir -p "$STAGE/Localization/English"

dotnet "$DIVINE" -g bg3 -a convert-loca \
  -s "$HERE/Localization/English/StoneheartStorm.loca.xml" \
  -d "$STAGE/Localization/English/StoneheartStorm.loca"
[ -s "$STAGE/Localization/English/StoneheartStorm.loca" ] || { echo "loca conversion produced nothing"; exit 1; }

for f in "$STAGE"/Public/StoneheartStorm/RootTemplates/*.lsx; do
  [ -e "$f" ] || continue
  dotnet "$DIVINE" -g bg3 -a convert-resource -s "$f" -d "${f%.lsx}.lsf"
  [ -s "${f%.lsx}.lsf" ] || { echo "template conversion failed: $f"; exit 1; }
  rm "$f"
done

rm -f "$OUT"
dotnet "$DIVINE" -g bg3 -a create-package -s "$STAGE" -d "$OUT" -c lz4
[ -s "$OUT" ] || { echo "pak not created"; exit 1; }

# Verify: extract and confirm key files are inside
CHECK="$HERE/.check"; rm -rf "$CHECK"
dotnet "$DIVINE" -g bg3 -a extract-package -s "$OUT" -d "$CHECK"
for f in Mods/StoneheartStorm/meta.lsx \
         Public/StoneheartStorm/ClassDescriptions/ClassDescriptions.lsx \
         Public/StoneheartStorm/Progressions/Progressions.lsx \
         Public/StoneheartStorm/RootTemplates/SSTORM_Backpack.lsf \
         Public/StoneheartStorm/RootTemplates/SSTORM_Items.lsf \
         Localization/English/StoneheartStorm.loca; do
  [ -s "$CHECK/$f" ] || { echo "MISSING in pak: $f"; exit 1; }
done
rm -rf "$CHECK" "$STAGE"
echo "BUILD_OK $OUT"
