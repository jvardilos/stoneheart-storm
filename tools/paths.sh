#!/usr/bin/env bash
# Shared, overridable paths for the build/install/extract scripts. Source this file.
#   BG3_DATA  – the game's Data folder (holds Shared.pak, Gustav.pak, ...)
#   BG3_USER  – the "Larian Studios/Baldur's Gate 3" user folder (holds Mods/ and PlayerProfiles/)
# Set either variable yourself to override the per-OS defaults below.

_bg3="Baldur's Gate 3"
case "$(uname -s)" in
  Darwin)
    _data="$HOME/Library/Application Support/Steam/steamapps/common/Baldurs Gate 3/$_bg3.app/Contents/Data"
    _user="$HOME/Documents/Larian Studios/$_bg3"
    ;;
  MINGW*|MSYS*|CYGWIN*)   # Git Bash on Windows
    _data="/c/Program Files (x86)/Steam/steamapps/common/Baldurs Gate 3/Data"
    _user="$(cygpath -u "$LOCALAPPDATA")/Larian Studios/$_bg3"
    ;;
  Linux)                  # Steam / Proton (incl. Steam Deck)
    _steam="${STEAM_ROOT:-$HOME/.steam/steam}"
    _data="$_steam/steamapps/common/Baldurs Gate 3/Data"
    _user="$_steam/steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/$_bg3"
    ;;
  *)
    echo "Unknown OS $(uname -s): set BG3_DATA and BG3_USER yourself." >&2
    _data=""; _user=""
    ;;
esac
[ -n "${BG3_DATA:-}" ] || BG3_DATA="$_data"
[ -n "${BG3_USER:-}" ] || BG3_USER="$_user"
export BG3_DATA BG3_USER

# The required "DnD 5.5e All-in-One BEYOND" mod (this mod is built on top of it).
DND55_UUID="897914ef-5c96-053c-44af-0be823f895fe"
dnd55_pak() { ls "$BG3_USER"/Mods/dnd2024_*.pak 2>/dev/null | head -1; }
