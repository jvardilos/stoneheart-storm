# Stoneheart Storm

A Baldur's Gate 3 mod adding content from *Valda's Spire of Secrets* for a home campaign
(characters Vindr and Tulio), built on top of **DnD 5.5e All-in-One BEYOND**.

## What's in it
- **Warden** (new class) with all seven Champion's Calls: Stoneheart Defender, Bloodwrath Guardian,
  Grey Watchman, Nightgaunt, Soulblood Shaman, Storm Sentinel, Verdant Protector.
- **Paladin oaths**: Storms, Eternal Night, Heresy, Revelry, Sun, Winter (chosen at Paladin level 3,
  alongside 5.5e's oaths).
- **Craftsman** (new class) with masterwork properties as level-up picks and four guilds:
  Armigers, Bladeworkers, Forgeknight, Thunderlords.
- **Boogie Woogie** (homebrew Fighter subclass for Tulio): Cursed Energy and a place-swapping clap.
- Exotic weapons and armor, the Reverberating Shield, and a backpack added to the tutorial chest.

Features past level 12 need a level-cap mod (e.g. UnlockLevelCurve). Many features are
approximations of the book where BG3 has no equivalent; see the generator scripts for notes.

## Requirements
- Baldur's Gate 3 (Patch 8) and the **DnD 5.5e All-in-One BEYOND** mod, installed and enabled
  (plus that mod's own dependencies). Stoneheart Storm must load **after** it; `install.sh` does this.
- .NET 8 SDK (`dotnet`), Python 3, git, and bash (macOS/Linux; Git Bash on Windows).

## Build and install
```bash
tools/setup_divine.sh        # once: builds a pack/unpack tool (LSLib "divine") into tools/divine/
./build.sh                   # -> dist/StoneheartStorm.pak
./install.sh                 # copies the pak into BG3's Mods folder and registers it after 5.5e
```
Quit BG3 before installing (the game rewrites `modsettings.lsx` on exit). `install.sh` backs up
`modsettings.lsx` first and refuses if 5.5e isn't installed and enabled.

The 5.5e dependency is enforced by `install.sh`, **not declared in `Mods/StoneheartStorm/meta.lsx`**:
declaring it made the game silently drop this mod from the load order (5.5e itself depends on
ImprovedUI, which may be the reason). Only add it back if every 5.5e dependency is installed.

Game/user paths are detected per OS in `tools/paths.sh`; override with `BG3_DATA=...` (the game's
`Data` folder) and `BG3_USER=...` (the `Larian Studios/Baldur's Gate 3` folder).

## Editing content
Most content is generated; edit the generator, re-run it, then build:

| Script | Generates |
|---|---|
| `tools/gen_oaths.py` | the five Valda oaths |
| `tools/gen_warden.py` | Warden calls, Warden's Mark, subclass list, multiclass row |
| `tools/gen_craftsman.py` | Craftsman class, masterwork picks, guilds |
| `tools/gen_item_templates.py` | item root templates (borrowed models) |
| `tools/gen_overrides.py` | the 5.5e Paladin/Fighter rows extended with this mod's subclasses |

The generators and `tools/check_refs.py` need game data extracted locally:
```bash
tools/extract_game_data.sh   # -> .cache/ (gitignored: Larian data, never committed)
```
`check_refs.py` (run by `build.sh` when `.cache/` exists) fails the build if any spell, status,
passive, interrupt or icon the mod references doesn't exist in the mod, the game, or 5.5e.
After a game or 5.5e update, re-run the extract and `tools/gen_overrides.py`.
