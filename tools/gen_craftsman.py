#!/usr/bin/env python3
"""Generate the Craftsman class (Valda's Spire of Secrets).

Base class (levels 1-20, Intelligence-based Masterwork save DC), masterwork properties as level-up
passive picks (Apprentice 2, Journeyman 5, Master 11, Legendary 17), and six Artisans' Guilds:
Arcane Maesters, Armigers, Bladeworkers, Forgeknight, Thunderlords, Trappers. Calibarons and
Mechanauts are out of scope. Crafting/out-of-combat features (Active Crafting, Tool Belt,
Folded Steel, Eye for Quality, Flawless Construction, Uncanny Tool Belt, Magnum Opus) are not built.

Run: python3 -I tools/gen_craftsman.py   (then ./build.sh)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_common import (ENEMIES, SAVE, classes, entry, names, passive, reaction, resource, rows,  # noqa: E402
                        self_aura, self_hit_reaction, shout, status, subclass, target, write)
from modlib import PUB, attr, uid, upsert_lsx  # noqa: E402

CRAFTSMAN = uid("class:Craftsman")
TABLE = uid("table:Craftsman")
INT = "Intelligence"
ICON_W = "PassiveFeature_MultiattackDefense"
ICON_F = "Action_Paladin_HealingRadiance"
ICON_L = "Spell_Evocation_LightningBolt"
ICON_FIRE = "Spell_Evocation_ConeOfCold"
WEAPON = "IF(IsWeaponAttack()):"


def plist(key, title, passives):
    u = uid("plist:" + key)
    upsert_lsx(PUB / "Lists" / "PassiveLists.lsx",
               [f'<node id="PassiveList">{attr("Name", "FixedString", title)}{attr("Passives", "LSString", ",".join(passives))}{attr("UUID", "guid", u)}</node>'],
               region="PassiveLists")
    return u


# ------------------------------------------------------------------ masterwork properties (passive picks)
def mw(key, title, desc, boosts=None, **kw):
    name = f"SSTORM_MW_{key}"
    passive(name, f"Masterwork: {title}", desc, kw.pop("icon", ICON_W), boosts, **kw)
    return name


apprentice = [
    mw("Parrying", "Parrying", "While you aren't wielding a shield, you have +1 AC.", "IF(not HasShieldEquipped()):AC(1)"),
    mw("Scaled", "Scaled", "Your armor is covered in hardened scales: +1 AC.", "AC(1)"),
    mw("Integrated", "Integrated", "Your weapons are integrated into your armor: you can't be disarmed.", "StatusImmunity(DISARM)"),
    mw("Trip", "Trip", "Your weapon is built to hook and trip: advantage on Athletics checks, including shoves.", "Advantage(Skill, Athletics)"),
]
RESIST = ["Fire", "Cold", "Lightning", "Thunder", "Acid", "Poison", "Necrotic", "Radiant"]
journeyman = [
    mw("Magical1", "Magical (+1)", "Your masterwork weapon is magical: +1 to weapon attack and damage rolls.",
       f"{WEAPON}RollBonus(Attack,1);{WEAPON}DamageBonus(1)"),
    mw("AdamantineArmor", "Adamantine Armor", "Critical hits against you become normal hits.", "CriticalHit(AttackTarget,Success,Never)"),
    mw("MithralArmor", "Mithral Armor", "Your armor doesn't hinder stealth: advantage on Stealth checks (offsetting armor's disadvantage).",
       "Advantage(Skill, Stealth)"),
] + [mw(f"Resist{t}", f"Resistance ({t})", f"Your armor grants resistance to {t.lower()} damage.", f"Resistance({t}, Resistant)")
     for t in RESIST]
shout("Shout_SSTORM_MW_Trollskin", "Trollskin", "Bonus action: regain 1d10 + your craftsman level hit points. Once per short rest.",
      ICON_F, "RegainHitPoints(1d10+ClassLevel(Craftsman))", "BonusActionPoint:1", cooldown="OncePerShortRest", VerbalIntent="Healing")
SLAY = [("Undead", "UNDEAD"), ("Fiends", "FIEND"), ("Dragons", "DRAGON"), ("Aberrations", "ABERRATION")]
UF = "(Tagged('UNDEAD', context.Target) or Tagged('FIEND', context.Target))"
master = [
    mw("Keen", "Keen", "Your weapon scores a critical hit on a roll of 19 or 20.", f"{WEAPON}ReduceCriticalAttackThreshold(1)"),
    mw("Venom", "Venom", "Your weapon deals an extra 1d8 poison damage.", f"{WEAPON}CharacterWeaponDamage(1d8,Poison)"),
    mw("Blessed", "Blessed", "Your weapon deals an extra 1d4 radiant damage, or 1d10 against fiends and undead.",
       f"IF(IsWeaponAttack() and not {UF}):CharacterWeaponDamage(1d4,Radiant);IF(IsWeaponAttack() and {UF}):CharacterWeaponDamage(1d10,Radiant)"),
    mw("Magical2", "Magical (+1, Master)", "Another +1 to weapon attack and damage rolls (stacks with Journeyman Magical).",
       f"{WEAPON}RollBonus(Attack,1);{WEAPON}DamageBonus(1)"),
    mw("Trollskin", "Trollskin Armor", "Your armor is lined with troll skin: as a bonus action, regain 1d10 + your craftsman level hit points once per short rest.",
       "UnlockSpell(Shout_SSTORM_MW_Trollskin)", icon=ICON_F),
    mw("Winged", "Winged Armor", "Your armor has fold-out wings: you can fly.", "UnlockSpell(Projectile_Fly_Spell)"),
] + [mw(f"Elemental{t}", f"Elemental ({t})", f"Your weapon deals an extra 1d6 {t.lower()} damage.", f"{WEAPON}CharacterWeaponDamage(1d6,{t})")
     for t in ["Fire", "Cold", "Lightning", "Thunder", "Acid"]] + \
    [mw(f"Slaying{n}", f"Slaying ({n})", f"Your weapon deals an extra 1d12 damage to {n.lower()}.",
        f"IF(IsWeaponAttack() and Tagged('{tag}', context.Target)):CharacterWeaponDamage(1d12)") for n, tag in SLAY]
shout("Shout_SSTORM_MW_Mirror", "Mirrored Armor", "Cast Mirror Image without a spell slot. Once per short rest.",
      None, None, "ActionPoint:1", using="Shout_MirrorImage", cooldown="OncePerShortRest", Level="")
status("SSTORM_MW_IMMORTAL", "Immortal Armor", "The next time you drop to 0 hit points, you drop to 1 instead.",
       "PassiveFeature_RelentlessEndurance", "DownedStatus(RELENTLESS_ENDURANCE_DOWNED,5)")
legendary = [
    mw("Magical3", "Magical (+1, Legendary)", "Another +1 to weapon attack and damage rolls (stacks with the other Magical properties).",
       f"{WEAPON}RollBonus(Attack,1);{WEAPON}DamageBonus(1)"),
    mw("Vorpal", "Vorpal", "When you score a critical hit with a weapon, the target takes an extra 4d8 slashing damage.",
       context="OnDamage", conditions="IsCritical() and IsWeaponAttack()", functors="DealDamage(4d8,Slashing)"),
    mw("Fleet", "Fleet Armor", "+10 ft speed and +3 initiative.", "ActionResource(Movement,3,0);Initiative(3)"),
    mw("Immortal", "Immortal Armor", "Once per long rest, when you drop to 0 hit points you drop to 1 instead.",
       context="OnCreate;OnLongRest", functors="ApplyStatus(SELF,SSTORM_MW_IMMORTAL,100,-1)",
       props="Highlighted;OncePerLongRest", icon="PassiveFeature_RelentlessEndurance"),
    mw("Mirrored", "Mirrored Armor", "Cast Mirror Image without a spell slot once per short rest.", "UnlockSpell(Shout_SSTORM_MW_Mirror)"),
]
MW_LISTS = {lvl: plist(f"Craftsman:mw:{lvl}", f"Craftsman masterwork {tier}", ps) for lvl, tier, ps in
            [(2, "apprentice", apprentice), (5, "journeyman", journeyman), (11, "master", master), (17, "legendary", legendary)]}

# ------------------------------------------------------------------ Armigers' Guild
status("SSTORM_AR_SHINING", "Challenged by Shining Steel", "Disadvantage on attack rolls that don't target the Armiger.",
       "Spell_Enchantment_CompelledDuel", "IF(not HasStatus('SSTORM_AR_SHINING', context.Source, context.Target)):Disadvantage(AttackRoll)",
       negative=True)
shout("Shout_SSTORM_AR_ShiningSteel", "Shining Steel",
      "No action, once per combat. Challenge enemies within 60 feet: each makes a Wisdom saving throw against your Masterwork save DC or has disadvantage on attack rolls that don't target you for 1 round.",
      "Spell_Enchantment_CompelledDuel", None, "", cond=ENEMIES, area="18", cooldown="OncePerCombat",
      roll=SAVE("Wisdom"), succ="ApplyStatus(SSTORM_AR_SHINING,100,1)", save="Wisdom")
status("SSTORM_AR_BANDED", "Reinforced Armor (Banded)", "+1 AC until you're hit.", ICON_W, "AC(1)", RemoveEvents="OnDamage")
status("SSTORM_AR_ADAMANT", "Reinforced Armor (Adamant)", "The next damage you take is reduced by 4.", ICON_W,
       "DamageReduction(All,Flat,4)", RemoveEvents="OnDamage")
for key, title, st, d in [("Banded", "Reinforce Armor: Banded", "SSTORM_AR_BANDED", "+1 AC until the wearer is hit."),
                          ("Adamant", "Reinforce Armor: Adamant", "SSTORM_AR_ADAMANT", "The next damage the wearer takes is reduced by 4.")]:
    target(f"Target_SSTORM_AR_{key}", title, f"Reinforce an ally's armor (or your own). {d} Six reinforcements per short rest.",
           ICON_W, f"ApplyStatus({st},100,-1)", "ActionPoint:1;SSTORM_Reinforcement:1", "(Ally() or Self()) and not Dead() and Character()", radius="1.5")
resource("SSTORM_Reinforcement", "Armor Reinforcements", "Armor reinforcements you can apply. Six per short rest.", replenish="ShortRest")
shout("Shout_SSTORM_AR_Fortify", "Fortify", "Bonus action: you take half damage from all sources until the end of your next turn. Once per short rest.",
      ICON_W, "ApplyStatus(SSTORM_AR_FORTIFIED,100,2)", "BonusActionPoint:1", cooldown="OncePerShortRest")
status("SSTORM_AR_FORTIFIED", "Fortified", "Damage taken is halved.", ICON_W, "DamageReduction(All,Half)")
passive("SSTORM_AR_Invincible", "Invincible Armor",
        "Bludgeoning, piercing and slashing damage you take from nonmagical attacks is reduced by 5.", ICON_W,
        ";".join(f"IF(not HasDamageEffectFlag(DamageFlags.Magical)):DamageReduction({t}, Flat, 5)" for t in ["Bludgeoning", "Piercing", "Slashing"]))
AR_STYLES = plist("Armigers:styles", "Armigers' Guild fighting styles", ["FightingStyle_Defense", "FightingStyle_Protection"])
subclass(CRAFTSMAN, "ArmigersGuild", "Armigers' Guild",
         "Armorsmiths of great renown that wear reinforced steel. (Valda's Spire of Secrets)", {
             3: {"selectors": [f"SelectPassives({AR_STYLES},1,SSTORMArmigerStyle)"]},
             7: {"spells": ["Shout_SSTORM_AR_ShiningSteel"], "ability": INT},
             10: {"spells": ["Target_SSTORM_AR_Banded", "Target_SSTORM_AR_Adamant"], "ability": INT,
                  "boosts": "ActionResource(SSTORM_Reinforcement,6,0)"},
             14: {"spells": ["Shout_SSTORM_AR_Fortify"], "ability": INT},
             18: {"passives": ["SSTORM_AR_Invincible"]},
         }, sound="Fighter", casting_ability="4")

# ------------------------------------------------------------------ Bladeworkers' Guild
target("Target_SSTORM_BW_Disarm", "Sabotaging Strike: Disarm",
       "Once per turn, attempt to disarm a creature within reach: it makes a Strength saving throw against your Masterwork save DC or drops its weapon.",
       "Spell_Enchantment_CompelledDuel", None, "ActionPoint:1", ENEMIES, radius="1.5", cooldown=None,
       roll=SAVE("Strength"), succ="ApplyStatus(DISARM,100,0)", save="Strength", Cooldown="OncePerTurn")
target("Target_SSTORM_BW_Sunder", "Sabotaging Strike: Sunder",
       "Once per turn, shatter a creature's defenses: it makes a Dexterity saving throw against your Masterwork save DC or its armor suffers a -1 AC penalty until it's repaired (a long rest).",
       "Spell_Enchantment_CompelledDuel", None, "ActionPoint:1", ENEMIES, radius="1.5",
       roll=SAVE("Dexterity"), succ="ApplyStatus(SSTORM_BW_SUNDERED,100,-1)", save="Dexterity", Cooldown="OncePerTurn")
status("SSTORM_BW_SUNDERED", "Sundered", "Armor damaged: -1 AC.", "Spell_Enchantment_CompelledDuel", "AC(-1)", negative=True)
status("SSTORM_BW_HONED", "Honed Weapon", "+2 to your next weapon attack roll.", ICON_W, f"{WEAPON}RollBonus(Attack,2)", RemoveEvents="OnAttack")
status("SSTORM_BW_SHARPENED", "Sharpened Weapon", "Your next weapon attack deals an extra 1d8 damage.", ICON_W,
       f"{WEAPON}CharacterWeaponDamage(1d8)", RemoveEvents="OnAttack")
for key, title, st, d in [("Honed", "Fortify Weapon: Honed", "SSTORM_BW_HONED", "+2 to the next weapon attack roll."),
                          ("Sharpened", "Fortify Weapon: Sharpened", "SSTORM_BW_SHARPENED", "The next weapon attack deals an extra 1d8 damage.")]:
    target(f"Target_SSTORM_BW_{key}", title, f"Fortify an ally's weapon (or your own). {d} Six per short rest.",
           ICON_W, f"ApplyStatus({st},100,-1)", "ActionPoint:1;SSTORM_Honing:1", "(Ally() or Self()) and not Dead() and Character()", radius="1.5")
resource("SSTORM_Honing", "Weapon Fortifications", "Weapon fortifications you can apply. Six per short rest.", replenish="ShortRest")
shout("Shout_SSTORM_BW_VersatileStrike", "Versatile Weapon Master", "No action, once per turn: advantage on your next weapon attack roll.",
      ICON_W, "ApplyStatus(SSTORM_BW_VERSATILE,100,1)", "", cooldown="OncePerTurn")
status("SSTORM_BW_VERSATILE", "Versatile Weapon Master", "Advantage on your next weapon attack.", ICON_W,
       f"{WEAPON}Advantage(AttackRoll)", RemoveEvents="OnAttack")
passive("SSTORM_BW_Devastating", "Devastating", "Your weapons score a critical hit on a roll of 18-20.", ICON_W,
        f"{WEAPON}ReduceCriticalAttackThreshold(2)")
BW_STYLES = plist("Bladeworkers:styles", "Bladeworkers' Guild fighting styles",
                  ["FightingStyle_Dueling", "FightingStyle_GreatWeaponFighting", "FightingStyle_TwoWeaponFighting"])
subclass(CRAFTSMAN, "BladeworkersGuild", "Bladeworkers' Guild",
         "Weaponsmiths who build innovative implements of war and train in their use. (Valda's Spire of Secrets)", {
             3: {"selectors": [f"SelectPassives({BW_STYLES},1,SSTORMBladeworkerStyle)"]},
             7: {"spells": ["Target_SSTORM_BW_Disarm", "Target_SSTORM_BW_Sunder"], "ability": INT},
             10: {"spells": ["Target_SSTORM_BW_Honed", "Target_SSTORM_BW_Sharpened"], "ability": INT,
                  "boosts": "ActionResource(SSTORM_Honing,6,0)"},
             14: {"spells": ["Shout_SSTORM_BW_VersatileStrike"], "ability": INT},
             18: {"passives": ["SSTORM_BW_Devastating"]},
         }, sound="Fighter", casting_ability="4")

# ------------------------------------------------------------------ Forgeknight's Guild
passive("SSTORM_FK_PortableForge", "Portable Forge", "While carrying your forge you have resistance to fire damage, and you know Produce Flame (Intelligence).",
        ICON_FIRE, "Resistance(Fire, Resistant)")
passive("SSTORM_FK_ForgefiredArmory", "Forgefired Armory",
        "Your melee weapons are explosive: when you hit, the blast deals 1d6 fire damage to the target's allies within 5 feet.",
        ICON_FIRE, context="OnDamage", conditions="IsMeleeWeaponAttack()", functors="ApplyStatus(SSTORM_FK_BLAST,100,1)")
self_aura("SSTORM_FK_BLAST", "Forgefired Blast", "An explosion bursts from this creature.", ICON_FIRE, "1.5",
          "IF(Ally() and not Self()):ApplyStatus(SSTORM_FK_SCORCHED)", negative=True)
status("SSTORM_FK_SCORCHED", "Scorched", "Caught in a forgefired blast.", ICON_FIRE, None, negative=True,
       OnApplyFunctors="DealDamage(1d6,Fire,Magical)")
shout("Shout_SSTORM_FK_Superheat", "Superheated Weapons",
      "Plunge your weapon into your forge for 10 minutes: your next melee weapon hit deals an extra 1d6 fire damage.",
      ICON_FIRE, "ApplyStatus(SSTORM_FK_SUPERHEATED,100,100)", "ActionPoint:1")
status("SSTORM_FK_SUPERHEATED", "Superheated Weapon", "Your next melee weapon attack deals an extra 1d6 fire damage.", ICON_FIRE,
       "IF(IsMeleeWeaponAttack()):CharacterWeaponDamage(1d6,Fire)", RemoveEvents="OnAttack")
shout("Shout_SSTORM_FK_FireBurst", "Fire Burst",
      "Release your forge's heat in a colossal burst: each creature within 20 feet makes a Dexterity saving throw against your Masterwork save DC, taking 8d6 fire damage on a failure or half on a success. You take no damage. Once per short rest.",
      ICON_FIRE, None, "ActionPoint:1", cond="not Self() and not Dead() and Character()", area="6", cooldown="OncePerShortRest",
      roll=SAVE("Dexterity"), succ="DealDamage(8d6,Fire,Magical)", fail="DealDamage((8d6)/2,Fire,Magical)", save="Dexterity")
passive("SSTORM_FK_ForgePlate", "Forge Plate", "A miniature furnace in your armor: you're immune to fire damage.", ICON_FIRE,
        "Resistance(Fire, Immune)")
subclass(CRAFTSMAN, "ForgeknightsGuild", "Forgeknight's Guild",
         "Wields a portable forge to heat their weapons and armor to explosive limits. (Valda's Spire of Secrets)", {
             3: {"spells": ["Shout_ProduceFlame"], "ability": INT, "passives": ["SSTORM_FK_PortableForge"]},
             7: {"passives": ["SSTORM_FK_ForgefiredArmory"]},
             10: {"spells": ["Shout_SSTORM_FK_Superheat"], "ability": INT},
             14: {"spells": ["Shout_SSTORM_FK_FireBurst"], "ability": INT},
             18: {"passives": ["SSTORM_FK_ForgePlate"]},
         }, sound="Fighter", casting_ability="4")

# ------------------------------------------------------------------ Thunderlords' Guild
resource("SSTORM_ChargePoint", "Charge Points", "Electrical energy stored in your power cell. Regained on a short or long rest.",
         replenish="ShortRest")
ON_MY_MELEE_HIT = ("IsAbleToReact(context.Observer) and not Self() and not Item() and IsMeleeAttack() and "
                   "Self(context.Source,context.Observer) and HasDamageEffectFlag(DamageFlags.Hit)")
reaction("Interrupt_SSTORM_TL_Discharge", "Power Cell: Discharge", "Spend 1 charge point: the creature you hit takes an extra 1d6 lightning damage.",
         ICON_L, "OnCastHit", "Self", ON_MY_MELEE_HIT, "DealDamage(1d6,Lightning,Magical)", cost="SSTORM_ChargePoint:1")
reaction("Interrupt_SSTORM_TL_Overcharge", "Power Cell: Overcharge", "Spend 2 charge points: the creature you hit takes an extra 2d6 lightning damage.",
         ICON_L, "OnCastHit", "Self", ON_MY_MELEE_HIT, "DealDamage(2d6,Lightning,Magical)", cost="SSTORM_ChargePoint:2")
reaction("Interrupt_SSTORM_TL_Jolt", "Power Cell: Jolt", "Spend 1 charge point: the creature you hit can't take reactions until the start of your next turn.",
         ICON_L, "OnCastHit", "Self", ON_MY_MELEE_HIT, "ApplyStatus(OBSERVER_TARGET,SSTORM_SS_STATIC,100,1)", cost="SSTORM_ChargePoint:1")
passive("SSTORM_TL_PowerCell", "Power Cell",
        "Once per turn when you hit with a melee attack, spend charge points to Discharge (+1d6 lightning per point, up to 2) or Jolt (no reactions). Charge points equal half your craftsman level, regained on a short rest.",
        ICON_L, "UnlockInterrupt(Interrupt_SSTORM_TL_Discharge);UnlockInterrupt(Interrupt_SSTORM_TL_Overcharge);UnlockInterrupt(Interrupt_SSTORM_TL_Jolt)")
passive("SSTORM_TL_LightningRod", "Lightning Rod", "You have resistance to lightning damage.", ICON_L, "Resistance(Lightning, Resistant)")
shout("Shout_SSTORM_TL_StaticCharge", "Static Charge",
      "Store a charge in your weapon and armor for 10 minutes: your next weapon hit deals an extra 1d6 lightning damage, and the next time you're hit in melee you can use your reaction to deal 1d8 lightning damage to the attacker. Once per short rest.",
      ICON_L, "ApplyStatus(SSTORM_TL_CHARGED_WEAPON,100,100);ApplyStatus(SSTORM_TL_CHARGED_ARMOR,100,100)", "ActionPoint:1",
      cooldown="OncePerShortRest")
status("SSTORM_TL_CHARGED_WEAPON", "Charged Weapon", "Your next weapon hit deals an extra 1d6 lightning damage.", ICON_L,
       f"{WEAPON}CharacterWeaponDamage(1d6,Lightning)", RemoveEvents="OnAttack")
status("SSTORM_TL_CHARGED_ARMOR", "Charged Armor", "When hit in melee, you can discharge 1d8 lightning damage into the attacker.", ICON_L,
       "UnlockInterrupt(Interrupt_SSTORM_TL_ChargedArmor)")
reaction("Interrupt_SSTORM_TL_ChargedArmor", "Charged Armor", "Discharge your armor: the creature that hit you takes 1d8 lightning damage.",
         ICON_L, "OnCastHit", "Self",
         "IsAbleToReact(context.Observer) and Enemy(context.Source,context.Observer) and IsHit() and IsMeleeAttack() and not AnyEntityIsItem() and HasLastAttackTriggered()",
         "UseSpell(SWAP,Target_SSTORM_TL_ArmorDischarge,true,true,true);RemoveStatus(OBSERVER_OBSERVER,SSTORM_TL_CHARGED_ARMOR)")
target("Target_SSTORM_TL_ArmorDischarge", "Charged Armor", "1d8 lightning damage to a melee attacker.", ICON_L,
       "DealDamage(1d8,Lightning,Magical)", "", "Character() and not Dead()", radius="3")
dn, dd = names("Zone_SSTORM_TL_HighVoltage", "High Voltage", "Spend 5 charge points to cast Lightning Bolt without a spell slot, using your Masterwork save DC.")
entry("Spell_Zone.txt", "Zone_SSTORM_TL_HighVoltage", "SpellData",
      {"SpellType": "Zone", "Level": "", "UseCosts": "ActionPoint:1;SSTORM_ChargePoint:5", "DisplayName": dn, "Description": dd},
      using="Zone_LightningBolt")
target("Target_SSTORM_TL_Electroshock", "Electroshock",
       "Strike with your weapon and expend its built-in power cell: on a hit, the target makes a Constitution saving throw against your Masterwork save DC or is stunned until the end of your next turn. Once per short rest.",
       ICON_L, None, "ActionPoint:1", None, using="Target_AdvancedMeleeWeaponAction", radius=None, Cooldown="OncePerShortRest",
       SpellSuccess="DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);"
                    "IF(not SavingThrow(Ability.Constitution, SourceSpellDC())):ApplyStatus(STUNNED,100,1)",
       TooltipAttackSave="MeleeWeaponAttack;Constitution")
tl = {3: {"spells": ["Target_ShockingGrasp"], "ability": INT, "passives": ["SSTORM_TL_PowerCell"],
          "boosts": "ActionResource(SSTORM_ChargePoint,2,0)"},
      7: {"passives": ["SSTORM_TL_LightningRod"]},
      10: {"spells": ["Shout_SSTORM_TL_StaticCharge"], "ability": INT},
      14: {"spells": ["Zone_SSTORM_TL_HighVoltage"], "ability": INT},
      18: {"spells": ["Target_SSTORM_TL_Electroshock"], "ability": INT}}
for lvl in (5, 7, 9, 11, 13, 15, 17, 19):   # charge points = half craftsman level, rounded up
    tl.setdefault(lvl, {})["boosts"] = "ActionResource(SSTORM_ChargePoint,1,0)"
subclass(CRAFTSMAN, "ThunderlordsGuild", "Thunderlords' Guild",
         "An electric innovator that uses lightning-charged equipment. (Valda's Spire of Secrets)", tl,
         sound="Fighter", casting_ability="4")

# ------------------------------------------------------------------ Arcane Maesters' Guild
# Magic item crafting has no BG3 equivalent; each crafting tier instead grants the use of a few of the
# book's items as once-per-rest abilities. Instant Attunement and Resonant (18th) depend on attunement,
# which BG3 doesn't have, so they are not built.
ICON_AM = "Spell_Evocation_MagicMissile"
status("SSTORM_AM_ENCHANTED", "Enchanted Weapon", "This weapon is magical and uses its wielder's Intelligence for attack and damage rolls.",
       ICON_AM, "WeaponProperty(Magical);WeaponAttackRollAbilityOverride(Intelligence)")
shout("Shout_SSTORM_AM_Enchant", "Enchanted Weapon",
      "Weave enchantments into the weapon in your main hand: it becomes magical and you use Intelligence for its attack and damage rolls. Recast after switching weapons.",
      ICON_AM, "ApplyEquipmentStatus(MainHand,SSTORM_AM_ENCHANTED,100,-1)", "ActionPoint:1")
passive("SSTORM_AM_GogglesOfNight", "Goggles of Night", "You crafted goggles of night: you have darkvision out to 12m (40 ft).",
        "PassiveFeature_Darkvision", "DarkvisionRangeMin(12)")
shout("Shout_SSTORM_AM_Lantern", "Lantern of Revealing", "Your lantern of revealing shows invisible creatures: cast See Invisibility without a spell slot. Once per long rest.",
      None, None, "ActionPoint:1", using="Shout_SeeInvisibility", cooldown="OncePerLongRest", Level="")
dn, dd = names("Projectile_SSTORM_AM_Wand", "Wand of Magic Missiles", "Cast Magic Missile from your wand without a spell slot. Once per short rest.")
entry("Spell_Projectile.txt", "Projectile_SSTORM_AM_Wand", "SpellData",
      {"SpellType": "Projectile", "Level": "", "UseCosts": "ActionPoint:1", "Cooldown": "OncePerShortRest",
       "DisplayName": dn, "Description": dd}, using="Projectile_MagicMissile")
dn, dd = names("Projectile_SSTORM_AM_Circlet", "Circlet of Blasting", "Cast Scorching Ray from your circlet without a spell slot. Once per long rest.")
entry("Spell_Projectile.txt", "Projectile_SSTORM_AM_Circlet", "SpellData",
      {"SpellType": "Projectile", "Level": "", "UseCosts": "ActionPoint:1", "Cooldown": "OncePerLongRest",
       "DisplayName": dn, "Description": dd}, using="Projectile_ScorchingRay")
status("SSTORM_AM_EPHEMERAL", "Ephemeral Enchantment", "This weapon counts as magical.", ICON_AM, "WeaponProperty(Magical)")
target("Target_SSTORM_AM_Ephemeral", "Ephemeral Enchantment",
       "Lay an enchantment on an ally's main-hand weapon (or your own): it counts as magical for overcoming resistance and immunity.",
       ICON_AM, "ApplyEquipmentStatus(MainHand,SSTORM_AM_EPHEMERAL,100,-1)", "ActionPoint:1",
       "(Ally() or Self()) and not Dead() and Character()", radius="1.5")
dn, dd = names("Projectile_SSTORM_AM_WingedBoots", "Winged Boots", "Your winged boots let you cast Fly on yourself without a spell slot. Once per long rest.")
entry("Spell_Projectile.txt", "Projectile_SSTORM_AM_WingedBoots", "SpellData",
      {"SpellType": "Projectile", "Level": "", "UseCosts": "ActionPoint:1", "Cooldown": "OncePerLongRest",
       "DisplayName": dn, "Description": dd}, using="Projectile_Fly_Spell")
status("SSTORM_AM_SEVERED", "Severed Connection", "+4 AC and your Intelligence modifier to saving throws until the start of your next turn.",
       ICON_AM, "AC(4);RollBonus(SavingThrow,IntelligenceModifier)", TickType="StartTurn")
self_hit_reaction("Interrupt_SSTORM_AM_SeverConnection", "Sever Connection",
                  "When you're hit, break your bond with a magic item and repurpose its magic: +4 AC (possibly turning the hit into a miss) and your Intelligence modifier to saving throws until the start of your next turn. Once per short rest.",
                  ICON_AM, "ApplyStatus(OBSERVER_OBSERVER,SSTORM_AM_SEVERED,100,1)", Cooldown="OncePerShortRest")
passive("SSTORM_AM_SeverConnection", "Sever Connection", "Reaction when hit: +4 AC and Intelligence to saves until your next turn. Once per short rest.",
        ICON_AM, "UnlockInterrupt(Interrupt_SSTORM_AM_SeverConnection)")
status("SSTORM_AM_SPEED", "Boots of Speed", "Your movement speed is doubled.", "Spell_Transmutation_Haste", "ActionResourceMultiplier(Movement,200,0)")
shout("Shout_SSTORM_AM_BootsOfSpeed", "Boots of Speed", "Bonus action: click your heels together to double your movement speed for 10 turns. Once per long rest.",
      "Spell_Transmutation_Haste", "ApplyStatus(SSTORM_AM_SPEED,100,10)", "BonusActionPoint:1", cooldown="OncePerLongRest")
subclass(CRAFTSMAN, "ArcaneMaestersGuild", "Arcane Maesters' Guild",
         "Magical craftsmen that forge mundane steel into magic items. (Valda's Spire of Secrets)", {
             3: {"spells": ["Shout_SSTORM_AM_Enchant", "Shout_SSTORM_AM_Lantern"], "ability": INT,
                 "passives": ["SSTORM_AM_GogglesOfNight"]},
             7: {"spells": ["Projectile_SSTORM_AM_Wand", "Projectile_SSTORM_AM_Circlet"], "ability": INT},
             10: {"spells": ["Target_SSTORM_AM_Ephemeral", "Projectile_SSTORM_AM_WingedBoots"], "ability": INT},
             14: {"spells": ["Shout_SSTORM_AM_BootsOfSpeed"], "ability": INT, "passives": ["SSTORM_AM_SeverConnection"]},
         }, sound="Fighter", casting_ability="4")

# ------------------------------------------------------------------ Trappers' Guild
# Traps are summoned invisible helpers (the vanilla Silence spell's helper item) carrying an aura, the way
# vanilla Moonbeam works; saves use the summoner's Intelligence DC (8 + proficiency + Intelligence), as
# Moonbeam does. Deploying costs a bonus action (the book: forgo one attack of the Attack action).
# Man-Trap and Trigger Bomb fire once: the triggering creature's status sets off a small explosion that
# finds the trap and spends it. Ballista Trap keeps firing at each creature that enters its range.
ICON_TR = "Spell_Transmutation_SpikeGrowth"
ICON_BOW = "PassiveFeature_CrossbowExpert_PointBlank"
HELPER = "edca6656-dc8c-410b-9f16-fcc02d5ed803"           # vanilla Helper_Spell_Silence (invisible spell helper)
MINE_FX = "4d883bd6-2686-41ef-bbe2-7499ba0da29d"          # vanilla Orthon mine status effect, so traps are visible
TR_DC = "CalculateSpellDC(Ability.Intelligence, GetSummoner(context.Source))"
BOOBY = "HasPassive('SSTORM_TR_BoobyTrap', GetSummoner(context.Source)) and not Combat()"
TRIPS = "Character() and not Dead() and not Ally() and not Tagged('INVISIBLE_HELPER')"
TRAP_FLAGS = "DisableOverhead;DisableCombatlog;DisablePortraitIndicator"
HIT_FLAGS = "DisableOverhead;InitiateCombat;BringIntoCombat"


def dmg(dice, dtype, half=False):
    """Damage functors that double the dice for a Booby Trap (7th level, triggered outside combat)."""
    n, die = dice.split("d")
    def d(x):
        return f"({x}d{die})/2" if half else f"{x}d{die}"
    return f"IF(not ({BOOBY})):DealDamage({d(n)},{dtype});IF({BOOBY}):DealDamage({d(int(n) * 2)},{dtype})"


def trap_carrier(name, title, desc, radius, hit_status):
    status(name, title, desc, ICON_TR, None, AuraRadius=radius, StatusPropertyFlags=TRAP_FLAGS, StatusEffect=MINE_FX,
           AuraStatuses=f"TARGET:IF({TRIPS}):ApplyStatus({hit_status},100,-1)")


def spender(name, carrier, then):
    """A tiny explosion around the triggering creature that finds the trap carrying `carrier` and applies `then` to it."""
    entry("Spell_Projectile.txt", name, "SpellData",
          {"SpellType": "Projectile", "SpellProperties": f"IF(HasStatus('{carrier}')):ApplyStatus({then},100,1)",
           "ExplodeRadius": "1.5", "TargetConditions": f"HasStatus('{carrier}')"})


def deploy(name, title, desc, props, radius, area="1", costs="BonusActionPoint:1;SSTORM_TrapDeploy:1"):
    target(name, title, desc, ICON_TR, props, costs, None, radius=radius, AreaRadius=area,
           VerbalIntent="Damage", SpellFlags="CannotTargetCharacter;CannotTargetItems;IsHarmful")


resource("SSTORM_TrapDeploy", "Trap Deployments", "Traps you can deploy. Regained on a short or long rest.", replenish="ShortRest")
SUMMON = "GROUND:Summon(" + HELPER + ",100,,,,{})"

# Man-Trap: Dexterity save or 2d8 slashing and trapped (can't move); half on a success. Fires once.
status("SSTORM_TR_CLAMPED", "Caught in a Man-Trap", "Clamped in a hunting trap: can't move.", ICON_TR,
       "ActionResourceBlock(Movement)", negative=True, TickType="EndTurn")
status("SSTORM_TR_MANTRAP_SNAP", "Man-Trap", "A man-trap snapped shut on this creature.", ICON_TR, None, negative=True,
       StatusPropertyFlags=HIT_FLAGS,
       OnApplyRoll=f"not SavingThrow(Ability.Dexterity, {TR_DC})",
       OnApplySuccess=dmg("2d8", "Slashing") + ";ApplyStatus(SSTORM_TR_CLAMPED,100,2)",
       OnApplyFail=dmg("2d8", "Slashing", half=True),
       OnApplyFunctors="CreateExplosion(Projectile_SSTORM_TR_SpendManTrap)")
trap_carrier("SSTORM_TR_MANTRAP", "Man-Trap", "An oversized hunting trap, armed.", "1", "SSTORM_TR_MANTRAP_SNAP")
status("SSTORM_TR_SPENT", "Spent Trap", "This trap has gone off.", ICON_TR, None, StatusPropertyFlags=TRAP_FLAGS,
       OnApplyFunctors="RemoveStatus(SSTORM_TR_MANTRAP);Unsummon()")
spender("Projectile_SSTORM_TR_SpendManTrap", "SSTORM_TR_MANTRAP", "SSTORM_TR_SPENT")
deploy("Target_SSTORM_TR_ManTrap", "Trap: Man-Trap",
       "Set an oversized hunting trap on the ground nearby. The first creature to step on it makes a Dexterity saving throw against your Masterwork save DC: on a failure it takes 2d8 slashing damage and is trapped, unable to move, for 2 turns; on a success it takes half damage. Your allies don't trigger it.",
       SUMMON.format("SSTORM_TR_MANTRAP"), radius="3")

# Trigger Bomb: when a creature comes within 5 ft, it explodes: Dexterity save, 2d6 fire (half on a success),
# in 5 ft. The book's detonator reaction is automatic here.
status("SSTORM_TR_BOMB_TRIP", "Trigger Bomb", "Set off a trigger bomb.", "Action_Monster_Bombardement_ProjectileStrike", None, negative=True,
       StatusPropertyFlags=HIT_FLAGS, OnApplyFunctors="CreateExplosion(Projectile_SSTORM_TR_FindBomb)")
trap_carrier("SSTORM_TR_BOMB", "Trigger Bomb", "An explosive device, armed.", "1.5", "SSTORM_TR_BOMB_TRIP")
status("SSTORM_TR_DETONATE", "Detonating", "This bomb explodes.", ICON_TR, None, StatusPropertyFlags=TRAP_FLAGS,
       OnApplyFunctors="CreateExplosion(Projectile_SSTORM_TR_BombBlast);RemoveStatus(SSTORM_TR_BOMB);Unsummon()")
spender("Projectile_SSTORM_TR_FindBomb", "SSTORM_TR_BOMB", "SSTORM_TR_DETONATE")
entry("Spell_Projectile.txt", "Projectile_SSTORM_TR_BombBlast", "SpellData",
      {"SpellType": "Projectile", "ExplodeRadius": "1.5", "TargetConditions": "Character() and not Dead()",
       "SpellRoll": f"not SavingThrow(Ability.Dexterity, {TR_DC})",
       "SpellSuccess": dmg("2d6", "Fire").replace(BOOBY, BOOBY.replace("not Combat()", "not Combat(context.Target)")),
       "SpellFail": dmg("2d6", "Fire", half=True).replace(BOOBY, BOOBY.replace("not Combat()", "not Combat(context.Target)"))})
deploy("Target_SSTORM_TR_TriggerBomb", "Trap: Trigger Bomb",
       "Toss an explosive device up to 9m away. When a creature other than your allies comes within 1.5m of it, it explodes: each creature within 1.5m makes a Dexterity saving throw against your Masterwork save DC, taking 2d6 fire damage on a failure or half on a success.",
       SUMMON.format("SSTORM_TR_BOMB"), radius="9")

# Ballista Trap: fires at each creature that enters its range (6m around it, standing in for the book's
# 30-ft line): Dexterity save (standing in for the attack roll) or 2d8 piercing.
status("SSTORM_TR_BALLISTA_SHOT", "Ballista Trap", "Shot by a ballista trap.", ICON_BOW, None, negative=True,
       StatusPropertyFlags=HIT_FLAGS,
       OnApplyRoll=f"not SavingThrow(Ability.Dexterity, {TR_DC})", OnApplySuccess=dmg("2d8", "Piercing"))
trap_carrier("SSTORM_TR_BALLISTA", "Ballista Trap", "A compact ballista, loaded and aimed.", "6", "SSTORM_TR_BALLISTA_SHOT")
deploy("Target_SSTORM_TR_Ballista", "Trap: Ballista Trap",
       "Set up a compact ballista nearby. Each time a creature other than your allies comes within 6m of it, it fires: the creature makes a Dexterity saving throw against your Masterwork save DC or takes 2d8 piercing damage. Lasts 10 minutes.",
       SUMMON.format("SSTORM_TR_BALLISTA"), radius="1.5")

# Razor Wire: difficult terrain dealing 2d4 piercing per 1.5m moved (exactly vanilla Spike Growth's surface).
deploy("Target_SSTORM_TR_RazorWire", "Trap: Razor Wire",
       "Spread a tangle of razor wire nearby: the area becomes difficult terrain, and a creature moving through it takes 2d4 piercing damage for every 1.5m it travels. Razor wire can't be recovered.",
       "GROUND:CreateSurface(2,100,SpikeGrowth)", radius="3", area="2")

TRAP_SPELLS = ["Target_SSTORM_TR_ManTrap", "Target_SSTORM_TR_TriggerBomb", "Target_SSTORM_TR_Ballista", "Target_SSTORM_TR_RazorWire"]
passive("SSTORM_TR_BoobyTrap", "Booby Trap",
        "Your traps are hard to spot: a trap that goes off against a creature that isn't in combat yet deals twice as many damage dice.",
        ICON_TR)
status("SSTORM_TR_HAIRTRIGGER", "Hair-Trigger", "Advantage on your next ranged weapon attack.", ICON_BOW,
       "IF(IsRangedWeaponAttack()):Advantage(AttackRoll)", RemoveEvents="OnAttack")
passive("SSTORM_TR_AmbushModification", "Ambush Modification",
        "Your ranged weapons have hair-triggers: when combat starts, your first ranged weapon attack has advantage.",
        ICON_BOW, context="OnCombatStarted", functors="ApplyStatus(SELF,SSTORM_TR_HAIRTRIGGER,100,-1)")
status("SSTORM_TR_RAPID", "Rapid Setup", "Deploying traps costs no bonus action this turn.", ICON_TR,
       "UnlockSpellVariant(" + " or ".join(f"SpellId('{s}')" for s in TRAP_SPELLS)
       + ",ModifyUseCosts(Replace,BonusActionPoint,0,0,BonusActionPoint))")
shout("Shout_SSTORM_TR_RapidSetup", "Rapid Setup",
      "For the rest of this turn, deploying traps doesn't cost a bonus action (each still uses a deployment), so you can lay out several at once. Once per short rest.",
      ICON_TR, "ApplyStatus(SSTORM_TR_RAPID,100,1)", "ActionPoint:1", cooldown="OncePerShortRest")
status("SSTORM_TR_NETTED", "Netted", "Tangled in a net: can't move, attacks against it have advantage and its attacks have disadvantage.",
       ICON_TR, "ActionResourceBlock(Movement);Disadvantage(AttackRoll);Advantage(AttackTarget)", negative=True, TickType="EndTurn")
passive("SSTORM_TR_Net", "Net (Legendary property)",
        "Once per turn, when you hit a creature with a ranged weapon attack, a net deploys and entangles it until the end of its next turn.",
        ICON_TR, context="OnDamage", conditions="IsRangedWeaponAttack() and HasDamageEffectFlag(DamageFlags.Hit)",
        functors="ApplyStatus(SSTORM_TR_NETTED,100,1)", props="Highlighted;OncePerTurn")
tr = {3: {"spells": TRAP_SPELLS, "ability": INT, "passives": ["DangerSense"], "boosts": "ActionResource(SSTORM_TrapDeploy,3,0)"},
      7: {"passives": ["SSTORM_TR_BoobyTrap"]},
      10: {"passives": ["SSTORM_TR_AmbushModification"]},
      14: {"spells": ["Shout_SSTORM_TR_RapidSetup"], "ability": INT},
      18: {"passives": ["SSTORM_TR_Net"]}}
for lvl in (8, 12):   # deployments = Intelligence modifier in the book; fixed 3, 4, 5 here
    tr.setdefault(lvl, {})["boosts"] = "ActionResource(SSTORM_TrapDeploy,1,0)"
subclass(CRAFTSMAN, "TrappersGuild", "Trappers' Guild",
         "A mechanical tinkerer that deploys lethal booby traps during combat. (Valda's Spire of Secrets)", tr,
         sound="Fighter", casting_ability="4")

# ------------------------------------------------------------------ the Craftsman base class
GUILDS = [uid("class:" + n) for n in ["ArcaneMaestersGuild", "ArmigersGuild", "BladeworkersGuild", "ForgeknightsGuild",
                                      "ThunderlordsGuild", "TrappersGuild"]]
SKILLS = uid("skills:Craftsman")
upsert_lsx(PUB / "Lists" / "SkillLists.lsx",
           [f'<node id="SkillList">{attr("Name", "FixedString", "Craftsman Skill List")}'
            f'{attr("Skills", "LSString", "Arcana, Athletics, History, Investigation, Medicine, Perception, Persuasion")}'
            f'{attr("UUID", "guid", SKILLS)}</node>'], region="SkillLists")
ARMS = "Proficiency(LightArmor);Proficiency(MediumArmor);Proficiency(HeavyArmor);Proficiency(Shields);Proficiency(SimpleWeapons);Proficiency(MartialWeapons)"
base = {
    1: {"Boosts": "ProficiencyBonus(SavingThrow,Constitution);ProficiencyBonus(SavingThrow,Intelligence);" + ARMS,
        "Selectors": f"SelectSkills({SKILLS},2);SelectAbilityBonus(b9149c8e-52c8-46e5-9cb6-fc39301c05fe,AbilityBonus,2,1)"},
    2: {"Selectors": f"SelectPassives({MW_LISTS[2]},1,SSTORMMasterwork)"},
    3: {}, 4: {"AllowImprovement": True}, 5: {"PassivesAdded": "ExtraAttack", "Selectors": f"SelectPassives({MW_LISTS[5]},1,SSTORMMasterwork)"},
    6: {}, 7: {}, 8: {"AllowImprovement": True}, 9: {}, 10: {},
    11: {"Selectors": f"SelectPassives({MW_LISTS[11]},1,SSTORMMasterwork)"}, 12: {"AllowImprovement": True},
    13: {}, 14: {}, 15: {}, 16: {"AllowImprovement": True}, 17: {"Selectors": f"SelectPassives({MW_LISTS[17]},1,SSTORMMasterwork)"},
    18: {}, 19: {"AllowImprovement": True}, 20: {},
}


def base_row(level, spec, multiclass=False, subclasses=False):
    x = ((attr("AllowImprovement", "bool", "true") if spec.get("AllowImprovement") else "")
         + (attr("Boosts", "LSString", spec["Boosts"]) if spec.get("Boosts") else "")
         + (attr("IsMulticlass", "bool", "true") if multiclass else "")
         + attr("Level", "uint8", level) + attr("Name", "LSString", "Craftsman")
         + (attr("PassivesAdded", "LSString", spec["PassivesAdded"]) if spec.get("PassivesAdded") else "")
         + attr("ProgressionType", "uint8", "0")
         + (attr("Selectors", "LSString", spec["Selectors"]) if spec.get("Selectors") else "")
         + attr("TableUUID", "guid", TABLE)
         + attr("UUID", "guid", uid(f"row:Craftsman:{level}" + (":multiclass" if multiclass else ""))))
    kids = ""
    if subclasses:
        kids = '<children><node id="SubClasses"><children>' + "".join(
            f'<node id="SubClass">{attr("Object", "guid", g)}</node>' for g in GUILDS) + "</children></node></children>"
    return f'<node id="Progression">{x}{kids}</node>'


for lvl, spec in base.items():
    rows.append(base_row(lvl, spec, subclasses=(lvl == 3)))
rows.append(base_row(1, {"Boosts": "Proficiency(LightArmor);Proficiency(MediumArmor);Proficiency(Shields);Proficiency(SimpleWeapons);Proficiency(MartialWeapons)"},
                     multiclass=True))
dn, dd = names("class:Craftsman", "Craftsman",
               "A master of forge and workshop who builds masterwork arms and armor and fights with them. Masterwork properties are chosen as you level. (Valda's Spire of Secrets)")
classes.append('<node id="ClassDescription">' + attr("BaseHp", "int32", "10")
               + attr("CharacterCreationPose", "guid", "0f07ec6e-4ef0-434e-9a51-1353260ccff8")
               + f'<attribute id="Description" type="TranslatedString" handle="{dd[:-2]}" version="1"/>'
               + f'<attribute id="DisplayName" type="TranslatedString" handle="{dn[:-2]}" version="1"/>'
               + attr("HasGod", "bool", "false") + attr("HpPerLevel", "int32", "6") + attr("LearningStrategy", "uint8", "1")
               + attr("MulticlassSpellcasterModifier", "double", "0") + attr("MustPrepareSpells", "bool", "false")
               + attr("Name", "FixedString", "Craftsman") + attr("PrimaryAbility", "uint8", "1")
               + attr("ProgressionTableUUID", "guid", TABLE) + attr("SoundClassType", "FixedString", "Fighter")
               + attr("SpellCastingAbility", "uint8", "4") + attr("UUID", "guid", CRAFTSMAN) + "</node>")
write("CRAFTSMAN")
