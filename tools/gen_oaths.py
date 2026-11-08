#!/usr/bin/env python3
"""Generate the five Valda's Spire of Secrets Paladin oaths (Eternal Night, Heresy, Revelry, Sun, Winter).

Writes (idempotently, via modlib upserts): ClassDescriptions, Progressions, SpellLists,
ActionResourceDefinitions, stats entries and localization. Re-run after editing; then run
tools/gen_overrides.py (adds the oaths to the Paladin subclass lists) and ./build.sh.

BG3 oath-spell levels are 3/5/9/13/17; the book's five spell rows map onto those in order.
Features past level 12 (15, 20) only fire with a level-cap mod.
Run: python3 -I tools/gen_oaths.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modlib import (PALADIN, PUB, attr, handle, uid, upsert_lsx, upsert_loca, upsert_stats)  # noqa: E402

SHOUT_ANIM = ("83fb0115-57dd-4cce-ac40-87182b2865e2,,;,,;eb4f3d5f-6815-4ad5-a5af-870942af0863,,;"
              "ba5068a2-ed31-4b9a-87cc-be28edb9ad25,,;42014429-21fb-412d-bba6-0f8216f5e502,,;,,;"
              "43fa5e31-ad7e-47a9-9ca2-f6d40ba8e1cf,,;,,;,,")
TARGET_ANIM = ("554a18f7-952e-494a-b301-7702a85d4bc9,,;,,;af94aac1-d8eb-4ccb-9520-694ade11b61c,,;"
               "f5db4001-b136-4c48-9aa4-026c4a7dd3b7,,;22dfbbf4-f417-4c84-b39e-2039315961e6,,;,,;"
               "5bfbe9f9-4fc3-4f26-b112-43d404db6a89,,;,,;,,")
PREP, CAST = "f719faf1-83e7-4407-a2f2-0880e26f9ca5", "a851aded-d542-482c-81ea-aa807d8b630f"
CD = "ChannelOath:1"

stats = {"Spell_Shout.txt": [], "Spell_Target.txt": [], "Spell_Zone.txt": [], "Status_BOOST.txt": [],
         "Passive.txt": [], "Interrupt.txt": []}
loca = {}
lists, rows, classes, resources = [], [], [], []


def names(key, title, desc):
    n, d = handle(key + ":name"), handle(key + ":desc")
    loca[n], loca[d] = title, desc
    return f"{n};1", f"{d};1"


def entry(file, name, type_, fields, using=None):
    lines = [f'new entry "{name}"', f'type "{type_}"']
    fields = dict(fields)
    if "SpellType" in fields:
        lines.append(f'data "SpellType" "{fields.pop("SpellType")}"')
    if using:
        lines.append(f'using "{using}"')
    lines += [f'data "{k}" "{v}"' for k, v in fields.items() if v is not None]
    stats[file].append("\n".join(lines))


def status(name, title, desc, icon, boosts=None, using=None, negative=False, **extra):
    dn, dd = names(name, title, desc)
    f = {"StatusType": "BOOST", "DisplayName": dn, "Description": dd, "Icon": icon, "StackId": name,
         "Boosts": boosts, "StatusPropertyFlags": "DisableOverhead"}
    if negative:
        f["ManagedStatusEffectType"] = "Negative"
    f.update(extra)
    entry("Status_BOOST.txt", name, "StatusData", f, using)


def shout(name, title, desc, icon, props, costs, cond="Self()", area=None, cooldown=None, roll=None,
          succ=None, fail=None, using=None, save=None, **extra):
    dn, dd = names(name, title, desc)
    f = {"SpellType": "Shout", "Cooldown": cooldown, "SpellProperties": props, "AreaRadius": area,
         "TargetConditions": cond, "SpellRoll": roll, "SpellSuccess": succ, "SpellFail": fail,
         "TooltipAttackSave": save, "Icon": icon, "DisplayName": dn, "Description": dd,
         "CastTextEvent": "Cast", "UseCosts": costs}
    if not using:
        f.update({"SpellAnimation": SHOUT_ANIM, "VerbalIntent": "Utility", "SpellStyleGroup": "Class",
                  "PrepareEffect": PREP, "CastEffect": CAST})
    f.update(extra)
    entry("Spell_Shout.txt", name, "SpellData", f, using)


def target(name, title, desc, icon, props, costs, cond, radius="9", using=None, roll=None, succ=None,
           fail=None, save=None, **extra):
    dn, dd = names(name, title, desc)
    f = {"SpellType": "Target", "SpellProperties": props, "TargetRadius": radius, "TargetConditions": cond,
         "SpellRoll": roll, "SpellSuccess": succ, "SpellFail": fail, "TooltipAttackSave": save,
         "Icon": icon, "DisplayName": dn, "Description": dd, "CastTextEvent": "Cast", "UseCosts": costs}
    if not using:
        f.update({"SpellAnimation": TARGET_ANIM, "VerbalIntent": "Utility", "SpellStyleGroup": "Class",
                  "SpellFlags": "HasHighGroundRangeExtension;RangeIgnoreVerticalThreshold"})
    f.update(extra)
    entry("Spell_Target.txt", name, "SpellData", f, using)


def passive(name, title, desc, icon, boosts=None, context=None, conditions=None, functors=None,
            props="Highlighted"):
    dn, dd = names(name, title, desc)
    entry("Passive.txt", name, "PassiveData",
          {"DisplayName": dn, "Description": dd, "Icon": icon, "Properties": props, "Boosts": boosts,
           "StatsFunctorContext": context, "Conditions": conditions, "StatsFunctors": functors})


def self_hit_reaction(name, title, desc, icon, props, cost="ReactionActionPoint:1"):
    """Reaction offered when an attack hits you (pattern of vanilla self-scope OnPostRoll reactions)."""
    dn, dd = names(name, title, desc)
    entry("Interrupt.txt", name, "InterruptData", {
        "DisplayName": dn, "Description": dd, "Icon": icon, "InterruptContext": "OnPostRoll",
        "InterruptContextScope": "Self", "Container": "YesNoDecision",
        "Conditions": "IsAbleToReact(context.Observer) and Self(context.Target,context.Observer) and "
                      "HasDamageEffectFlag(DamageFlags.Hit) and not AnyEntityIsItem()",
        "Properties": props, "Cost": cost, "Stack": name, "InterruptDefaultValue": "Ask;Enabled",
        "EnableCondition": "not HasStatus('SG_Incapacitated')", "EnableContext": "OnStatusApplied;OnStatusRemoved"})


def aura(prefix, title, desc, icon, buff_boosts, radius="3"):
    """Vanilla-style paladin aura: a free toggle shout applying a permanent aura status."""
    aura_status, buff = f"SSTORM_{prefix}_AURA", f"SSTORM_{prefix}_AURA_BUFF"
    status(buff, title, desc, icon, buff_boosts)
    status(aura_status, title, desc, icon, None, AuraRadius=radius,
           AuraStatuses=f"IF(Ally() and not Tagged('INANIMATE')):ApplyStatus({buff})")
    shout(f"Shout_SSTORM_{prefix}_Aura", title, desc, icon, f"ApplyStatus({aura_status},100,-1)", "",
          RequirementConditions=f"not HasStatus('{aura_status}')", VerbalIntent="Buff")
    return f"Shout_SSTORM_{prefix}_Aura"


PB_TIERS = [(None, 4, 2), (4, 8, 3), (8, 12, 4), (12, 16, 5), (16, None, 6)]


def per_pb(dice_per_pb, die, dtype, half=False):
    """'N dice per point of proficiency bonus', as a chain of level-gated DealDamage functors."""
    out = []
    for lo, hi, pb in PB_TIERS:
        c = ([f"CharacterLevelGreaterThan({lo})"] if lo else []) + ([f"not CharacterLevelGreaterThan({hi})"] if hi else [])
        dmg = f"{dice_per_pb * pb}{die}"
        out.append(f"IF({' and '.join(c)}):DealDamage({'(' + dmg + ')/2' if half else dmg},{dtype},Magical)")
    return ";".join(out)


def resource(name, title, desc):
    dn, dd = names("res:" + name, title, desc)
    resources.append(f'<node id="ActionResourceDefinition">{attr("Description", "TranslatedString", "")}</node>'
                     .replace(attr("Description", "TranslatedString", ""),
                              f'<attribute id="Description" type="TranslatedString" handle="{dd[:-2]}" version="1"/>'
                              f'<attribute id="DisplayName" type="TranslatedString" handle="{dn[:-2]}" version="1"/>'
                              + attr("MaxLevel", "uint32", "0") + attr("Name", "FixedString", name)
                              + attr("ReplenishType", "FixedString", "Rest")
                              + attr("ShowOnActionResourcePanel", "bool", "true")
                              + attr("UUID", "guid", uid("res:" + name))))


def spell_list(key, title, spells):
    u = uid("list:" + key)
    lists.append(f'<node id="SpellList">{attr("Name", "FixedString", title)}'
                 f'{attr("Spells", "LSString", ";".join(spells))}{attr("UUID", "guid", u)}</node>')
    return u


def oath(name, title, desc, levels):
    """levels: {level: {"oath": [spells], "spells": [granted spells], "passives": [names]}}"""
    table = uid("table:" + name)
    first_list = None
    for lvl, spec in sorted(levels.items()):
        sel = []
        if spec.get("oath"):
            u = spell_list(f"{name}:oath:{lvl}", f"{title} oath spells level {lvl}", spec["oath"])
            first_list = first_list or u
            sel.append(f"AddSpells({u},OathSpells,,,AlwaysPrepared)")
        if spec.get("spells"):
            u = spell_list(f"{name}:feat:{lvl}", f"{title} features level {lvl}", spec["spells"])
            sel.append(f"AddSpells({u},,Charisma,,AlwaysPrepared)")
        x = (attr("Level", "uint8", lvl) + attr("Name", "LSString", name)
             + (attr("PassivesAdded", "LSString", ";".join(spec["passives"])) if spec.get("passives") else "")
             + attr("ProgressionType", "uint8", "1")
             + (attr("Selectors", "LSString", ";".join(sel)) if sel else "")
             + attr("TableUUID", "guid", table) + attr("UUID", "guid", uid(f"row:{name}:{lvl}")))
        rows.append(f'<node id="Progression">{x}</node>')
    dn, dd = names("class:" + name, title, desc)
    classes.append('<node id="ClassDescription">'
                   + attr("CharacterCreationPose", "guid", "0f07ec6e-4ef0-434e-9a51-1353260ccff8")
                   + f'<attribute id="Description" type="TranslatedString" handle="{dd[:-2]}" version="1"/>'
                   + f'<attribute id="DisplayName" type="TranslatedString" handle="{dn[:-2]}" version="1"/>'
                   + attr("LearningStrategy", "uint8", "1") + attr("MustPrepareSpells", "bool", "true")
                   + attr("Name", "FixedString", name) + attr("ParentGuid", "guid", PALADIN)
                   + attr("PrimaryAbility", "uint8", "1") + attr("ProgressionTableUUID", "guid", table)
                   + attr("SoundClassType", "FixedString", "Paladin") + attr("SpellCastingAbility", "uint8", "6")
                   + attr("SpellList", "guid", first_list) + attr("UUID", "guid", uid("class:" + name))
                   + "</node>")


ENEMIES = "Enemy() and not Dead() and Character()"
SAVE = lambda ab: f"not SavingThrow(Ability.{ab}, SourceSpellDC())"  # noqa: E731

# ---------------------------------------------------------------- Oath of Eternal Night
target("Target_SSTORM_EN_CoverOfDarkness", "Cover of Darkness",
       "Channel Divinity. As a bonus action, create a 15-foot-radius sphere of magical darkness at a point within 30 feet for 1 minute. You can see through darkness you create.",
       "Spell_Evocation_Darkness", None, f"BonusActionPoint:1;{CD}", None, using="Target_Darkness", Level="")
shout("Shout_SSTORM_EN_ShroudedArmor", "Shrouded Armor",
      "Channel Divinity. Imbue your armor with shadowstuff for 8 hours: add your Charisma modifier to Stealth checks, and your armor no longer imposes disadvantage on Stealth.",
      "Action_Hide", "ApplyStatus(SSTORM_EN_SHROUDED,100,4800)", f"ActionPoint:1;{CD}")
status("SSTORM_EN_SHROUDED", "Shrouded Armor", "Your armor reflects no light. Stealth checks gain your Charisma modifier, and armor doesn't impose disadvantage on them.",
       "Action_Hide", "Skill(Stealth, CharismaModifier);Advantage(Skill, Stealth)")
passive("SSTORM_EN_ShadowSight", "Raven's Sight", "You can see through magical darkness.",
        "Spell_Evocation_Darkness", "StatusImmunity(BLINDED_DARKNESS)")
en_aura = aura("EN_SLIP", "Slip into the Shadows",
               "Aura (10 ft). You and friendly creatures within it can take the Hide action as a bonus action.",
               "Action_Hide", "UnlockSpell(Shout_Hide_BonusAction)")
passive("SSTORM_EN_CloakOfNight", "Cloak of Night",
        "When you take damage, use your reaction to shed flakes of darkness: the next attack roll against you before the start of your next turn has disadvantage.",
        "Spell_Evocation_Darkness", "UnlockInterrupt(Interrupt_SSTORM_EN_CloakOfNight)")
self_hit_reaction("Interrupt_SSTORM_EN_CloakOfNight", "Cloak of Night",
                  "Use your reaction: the next attack roll against you before your next turn has disadvantage.",
                  "Spell_Evocation_Darkness", "ApplyStatus(OBSERVER_OBSERVER,SSTORM_EN_CLOAK,100,1)")
status("SSTORM_EN_CLOAK", "Cloak of Night", "The next attack roll against you has disadvantage.",
       "Spell_Evocation_Darkness", "Disadvantage(AttackTarget)", RemoveEvents="OnAttacked")
shout("Shout_SSTORM_EN_ShadowForm", "Shadow Form",
      "Become a tenebrous stalker for 1 hour. In dim light or darkness: advantage on Strength, Dexterity and Constitution checks; a bonus-action teleport of 60 feet into dim light or darkness; and once per turn your melee weapon hits deal an extra 3d6 necrotic damage. Once per long rest.",
      "Spell_Evocation_Darkness", "ApplyStatus(SSTORM_EN_SHADOW_FORM,100,600)", "ActionPoint:1", cooldown="OncePerRest")
DIM = "IF(not ObscuredState(ObscuredState.Clear)):"
status("SSTORM_EN_SHADOW_FORM", "Shadow Form", "In dim light or darkness you have advantage on Strength, Dexterity and Constitution checks, can teleport through the dark, and deal extra necrotic damage once per turn.",
       "Spell_Evocation_Darkness",
       f"{DIM}Advantage(Ability, Strength);{DIM}Advantage(Ability, Dexterity);{DIM}Advantage(Ability, Constitution);UnlockSpell(Target_SSTORM_EN_ShadowStep)")
target("Target_SSTORM_EN_ShadowStep", "Shadow Step",
       "Teleport up to 60 feet to an unoccupied space in dim light or darkness. You must be in dim light or darkness.",
       "Spell_Conjuration_MistyStep", None, "BonusActionPoint:1",
       "CanStand('') and not Character() and not Self() and not ObscuredStateAtPosition(ObscuredState.Clear)",
       radius="18", using="Target_MistyStep", Level="", SpellSchool="",
       RequirementConditions="not ObscuredState(ObscuredState.Clear)",
       SpellFlags="HasHighGroundRangeExtension;RangeIgnoreVerticalThreshold")
passive("SSTORM_EN_ShadowStrike", "Shadow Form: Necrotic Strike",
        "Once per turn while in Shadow Form and in dim light or darkness, a melee weapon hit deals an extra 3d6 necrotic damage.",
        "Spell_Evocation_Darkness", context="OnDamage", props="OncePerTurn;Highlighted",
        conditions="HasStatus('SSTORM_EN_SHADOW_FORM',context.Source) and IsMeleeWeaponAttack() and not ObscuredState(ObscuredState.Clear)",
        functors="DealDamage(3d6,Necrotic,Magical)")
oath("OathOfEternalNight", "Oath of Eternal Night",
     "A stealthy, brooding vigilante who metes out justice under cover of night. (Valda's Spire of Secrets)", {
         3: {"oath": ["Shout_FeatherFall", "Target_Longstrider"],
             "spells": ["Target_SSTORM_EN_CoverOfDarkness", "Shout_SSTORM_EN_ShroudedArmor"],
             "passives": ["SSTORM_EN_ShadowSight"]},
         5: {"oath": ["Shout_FindSteed", "Target_MistyStep"]},   # Find Steed from the 5.5e dependency
         7: {"spells": [en_aura]},
         9: {"oath": ["Target_Fly", "Target_Haste"]},
         13: {"oath": ["Teleportation_DimensionDoor", "Target_FreedomOfMovement"]},
         15: {"passives": ["SSTORM_EN_CloakOfNight"]},
         20: {"spells": ["Shout_SSTORM_EN_ShadowForm"], "passives": ["SSTORM_EN_ShadowStrike"]},
     })

# ---------------------------------------------------------------- Oath of Heresy
status("SSTORM_DEAFENED", "Deafened", "Can't hear. Disadvantage on Perception checks.",
       "Spell_Enchantment_CompelledDuel", "Disadvantage(Skill, Perception)", negative=True)
shout("Shout_SSTORM_HE_Blaspheme", "Blaspheme",
      "Channel Divinity. Speak profound, heretical words. Each enemy within 30 feet makes a Wisdom saving throw, taking 2d6 psychic damage per point of your proficiency bonus and becoming deafened for 1 minute on a failure, or half damage on a success.",
      "Spell_Enchantment_CompelledDuel", None, f"ActionPoint:1;{CD}", cond=ENEMIES, area="9",
      roll=SAVE("Wisdom"), succ=per_pb(2, "d6", "Psychic") + ";ApplyStatus(SSTORM_DEAFENED,100,10)",
      fail=per_pb(2, "d6", "Psychic", half=True), save="Wisdom")
shout("Shout_SSTORM_HE_TurnTheHoly", "Turn the Holy",
      "Channel Divinity. Celestials within 30 feet must make a Wisdom saving throw or be turned for 1 minute or until they take damage.",
      None, None, f"ActionPoint:1;{CD}", cond="Tagged('CELESTIAL')", using="Shout_TurnTheUnholy")
passive("SSTORM_HE_GodlessAura", "Godless Aura",
        "Use your reaction to counter a spell cast within 10 feet of you, without a spell slot (as a 3rd-level Counterspell).",
        "PassiveFeature_Counterspell", "UnlockInterrupt(Interrupt_SSTORM_HE_GodlessCounterspell)")
dn, dd = names("Interrupt_SSTORM_HE_GodlessCounterspell", "Godless Aura: Counterspell",
               "Counter a spell being cast within 10 feet of you, without a spell slot.")
entry("Interrupt.txt", "Interrupt_SSTORM_HE_GodlessCounterspell", "InterruptData", {
    "DisplayName": dn, "Description": dd, "Icon": "PassiveFeature_Counterspell",
    "InterruptContext": "OnSpellCast", "InterruptContextScope": "Nearby", "Container": "YesNoDecision",
    "Conditions": "not HasSpellCastBlocked(context.Observer) and IsAbleToReact(context.Observer) and not Self(context.Source, context.Observer) "
                  "and Enemy(context.Source, context.Observer) and IsSpell() and not Uninterruptible() and not HasStringInSpellRoll('WeaponAttack') "
                  "and not AnyEntityIsItem() and CounterspellCheck(context.Observer, context.Source) and not DistanceToEntityGreaterThan(3, context.ObserverPosition, context.Source)",
    "Roll": "TryCounterspellHigherLevel(3)",
    "Success": "Counterspell();UseSpell(OBSERVER_SOURCE,Target_Counterspell_Success,true,true,true)",
    "Failure": "UseSpell(OBSERVER_SOURCE,Target_Counterspell_Failure,true,true,true)",
    "Cost": "ReactionActionPoint:1", "InterruptDefaultValue": "Ask;Enabled",
    "EnableCondition": "not HasStatus('SG_Polymorph')", "EnableContext": "OnStatusApplied;OnStatusRemoved"})
resource("SSTORM_ImplacableWill", "Implacable Will", "Reroll a failed saving throw. Once per long rest.")
passive("SSTORM_HE_ImplacableWill", "Implacable Will",
        "When you fail a saving throw, you can reroll it. Once per long rest.",
        "PassiveFeature_Indomitable", "UnlockInterrupt(Interrupt_SSTORM_HE_ImplacableWill);ActionResource(SSTORM_ImplacableWill,1,0)")
dn, dd = names("Interrupt_SSTORM_HE_ImplacableWill", "Implacable Will", "Reroll the failed saving throw.")
entry("Interrupt.txt", "Interrupt_SSTORM_HE_ImplacableWill", "InterruptData", {
    "DisplayName": dn, "Description": dd, "Icon": "PassiveFeature_Indomitable",
    "InterruptContext": "OnPostRoll", "InterruptContextScope": "Self", "Container": "YesNoDecision",
    "Conditions": "not Dead(context.Observer) and HasInterruptedSavingThrow() and Self(context.Observer,context.Target) and not AnyEntityIsItem() and IsRerollInterruptInteresting()",
    "Properties": "SetReroll(19,true)", "Cost": "SSTORM_ImplacableWill:1",
    "InterruptDefaultValue": "Ask;Enabled", "EnableContext": "OnActionResourcesChanged"})
shout("Shout_SSTORM_HE_Apostate", "Apostate",
      "Assume an anti-apotheosis for 1 minute: you can Blaspheme as a bonus action without Channel Divinity (4d6 psychic, half on a save), and you gain 20 temporary hit points at the start of each of your turns. Once per long rest.",
      "Spell_Enchantment_CompelledDuel", "ApplyStatus(SSTORM_HE_APOSTATE,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_HE_APOSTATE", "Apostate", "You can Blaspheme as a bonus action and gain 20 temporary hit points at the start of each turn.",
       "Spell_Enchantment_CompelledDuel", "UnlockSpell(Shout_SSTORM_HE_ApostateBlaspheme)",
       TickType="StartTurn", TickFunctors="ApplyStatus(SSTORM_HE_APOSTATE_THP,100,1)")
status("SSTORM_HE_APOSTATE_THP", "Apostate's Defiance", "Temporary hit points from Apostate.",
       "Spell_Enchantment_CompelledDuel", "TemporaryHP(20)")
shout("Shout_SSTORM_HE_ApostateBlaspheme", "Blaspheme (Apostate)",
      "Bonus action. Each enemy within 30 feet makes a Wisdom saving throw: 4d6 psychic damage and deafened on a failure, half damage on a success.",
      "Spell_Enchantment_CompelledDuel", None, "BonusActionPoint:1", cond=ENEMIES, area="9", roll=SAVE("Wisdom"),
      succ="DealDamage(4d6,Psychic,Magical);ApplyStatus(SSTORM_DEAFENED,100,10)",
      fail="DealDamage((4d6)/2,Psychic,Magical)", save="Wisdom")
oath("OathOfHeresy", "Oath of Heresy",
     "A blasphemer and revolutionary who has turned their back on their faith. (Valda's Spire of Secrets)", {
         3: {"oath": ["Target_ProtectionFromEvilAndGood"],
             "spells": ["Shout_SSTORM_HE_Blaspheme", "Shout_SSTORM_HE_TurnTheHoly"]},
         5: {"oath": ["Target_MagicWeapon"]},
         7: {"passives": ["SSTORM_HE_GodlessAura"]},
         9: {"oath": ["Target_DispelMagic", "Target_SpeakWithDead"]},
         13: {"oath": ["Target_Banishment"]},
         15: {"passives": ["SSTORM_HE_ImplacableWill"]},
         17: {"oath": ["Shout_DispelEvilAndGood"]},
         20: {"spells": ["Shout_SSTORM_HE_Apostate"]},
     })

# ---------------------------------------------------------------- Oath of Revelry
target("Target_SSTORM_RE_ConjureDrink", "Conjure Drink",
       "Channel Divinity. Summon a frothy heavenly ale for up to three creatures: each has advantage on saving throws for the next minute.",
       "Action_Paladin_HealingRadiance", "ApplyStatus(SSTORM_RE_ALE,100,10)", f"ActionPoint:1;{CD}",
       "(Ally() or Self()) and not Dead() and Character()", radius="3", AmountOfTargets="3")
status("SSTORM_RE_ALE", "Heavenly Ale", "Advantage on saving throws.", "Action_Paladin_HealingRadiance",
       "Advantage(AllSavingThrows)")
shout("Shout_SSTORM_RE_SongAndDance", "Song and Dance",
      "Channel Divinity. Dance a catchy jig: each enemy within 15 feet makes a Wisdom saving throw or joins in, spending its movement dancing in place, with disadvantage on attack rolls and Dexterity saving throws. It repeats the save at the end of each of its turns.",
      "Spell_Enchantment_Tasha'sHideousLaughter", None, f"ActionPoint:1;{CD}", cond=ENEMIES, area="4.5",
      roll=SAVE("Wisdom"), succ="ApplyStatus(SSTORM_RE_DANCING,100,10)", save="Wisdom")
status("SSTORM_RE_DANCING", "Dancing", "Can't leave its space. Disadvantage on attack rolls and Dexterity saving throws. Repeats the Wisdom save at the end of each turn.",
       "Spell_Enchantment_Tasha'sHideousLaughter", "ActionResourceMultiplier(Movement,0,0);Disadvantage(SavingThrow, Dexterity);Disadvantage(AttackRoll)",
       negative=True, TickType="EndTurn", RemoveConditions="SavingThrow(Ability.Wisdom, SourceSpellDC())", RemoveEvents="OnTurn")
re_aura = aura("RE_FRATERNITY", "Aura of Fraternity",
               "Aura (5 ft). You and allies within it deal an extra 1d4 damage on melee weapon attacks.",
               "Action_Paladin_HealingRadiance", "IF(IsMeleeWeaponAttack()):CharacterWeaponDamage(1d4)", radius="1.5")
resource("SSTORM_Merrymaker", "Merrymaker", "Grant advantage to an ally's checks and saves. 3 per long rest.")
passive("SSTORM_RE_Merrymaker", "Merrymaker", "Three times per long rest, give yourself or a friendly creature within 30 feet advantage on its ability checks and saving throws until the start of your next turn.",
        "Action_Paladin_HealingRadiance", "ActionResource(SSTORM_Merrymaker,3,0)")
target("Target_SSTORM_RE_Merrymaker", "Merrymaker",
       "Give yourself or a friendly creature within 30 feet advantage on ability checks and saving throws until the start of your next turn. No action required.",
       "Action_Paladin_HealingRadiance", "ApplyStatus(SSTORM_RE_MERRY,100,1)", "SSTORM_Merrymaker:1",
       "(Ally() or Self()) and not Dead() and Character()")
status("SSTORM_RE_MERRY", "Merrymaker", "Advantage on ability checks and saving throws.", "Action_Paladin_HealingRadiance",
       "Advantage(AllSavingThrows);Advantage(AllAbilities)")
shout("Shout_SSTORM_RE_PartyAnimal", "Party Animal",
      "Become an embodiment of partying for 1 minute, emanating a 30-foot aura: you and allies in it can't be blinded, deafened or poisoned, and regain 10 hit points at the start of each of their turns. Once per long rest.",
      "Action_Paladin_HealingRadiance", "ApplyStatus(SSTORM_RE_PARTY_AURA,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_RE_PARTY", "Party Animal", "Can't be blinded, deafened or poisoned. Regain 10 hit points at the start of each turn.",
       "Action_Paladin_HealingRadiance", "StatusImmunity(SG_Blinded);StatusImmunity(SG_Poisoned);StatusImmunity(SSTORM_DEAFENED)",
       TickType="StartTurn", TickFunctors="RegainHitPoints(10)")
status("SSTORM_RE_PARTY_AURA", "Party Animal", "A 30-foot aura of gaiety.", "Action_Paladin_HealingRadiance", None,
       AuraRadius="9", AuraStatuses="IF(Ally() and not Tagged('INANIMATE')):ApplyStatus(SSTORM_RE_PARTY)")
oath("OathOfRevelry", "Oath of Revelry",
     "A party-paladin who keeps their allies dancing no matter what. (Valda's Spire of Secrets)", {
         3: {"oath": ["Target_CharmPerson", "Target_HideousLaughter"],
             "spells": ["Target_SSTORM_RE_ConjureDrink", "Shout_SSTORM_RE_SongAndDance"]},
         5: {"oath": ["Target_CalmEmotions", "Target_EnhanceAbility"]},
         7: {"spells": [re_aura]},
         9: {"oath": ["Target_HypnoticPattern"]},
         13: {"oath": ["Target_FreedomOfMovement"]},
         15: {"spells": ["Target_SSTORM_RE_Merrymaker"], "passives": ["SSTORM_RE_Merrymaker"]},
         20: {"spells": ["Shout_SSTORM_RE_PartyAnimal"]},
     })

# ---------------------------------------------------------------- Oath of the Sun
shout("Shout_SSTORM_SU_GloriousRadiance", "Glorious Radiance",
      "Channel Divinity. Radiate sunlight for 1 hour: gain temporary hit points equal to your paladin level + Charisma modifier. While they last, you can use your reaction when hit by a melee attack to deal 5 radiant damage to the attacker (10 at paladin level 11, 15 at 17).",
      "Action_Paladin_HealingRadiance", "ApplyStatus(SSTORM_SU_RADIANCE,100,600)", f"ActionPoint:1;{CD}")
status("SSTORM_SU_RADIANCE", "Glorious Radiance", "Temporary hit points from the sun; you can retaliate with radiant damage against melee attackers.",
       "Action_Paladin_HealingRadiance", "TemporaryHP(ClassLevel(Paladin)+CharismaModifier);UnlockInterrupt(Interrupt_SSTORM_SU_Radiance)",
       RemoveConditions="not HasTemporaryHP()", RemoveEvents="OnDamage")
dn, dd = names("Interrupt_SSTORM_SU_Radiance", "Glorious Radiance", "Deal radiant damage to the creature that hit you.")
entry("Interrupt.txt", "Interrupt_SSTORM_SU_Radiance", "InterruptData", {
    "DisplayName": dn, "Description": dd, "Icon": "Action_Paladin_HealingRadiance",
    "InterruptContext": "OnCastHit", "InterruptContextScope": "Self", "Container": "YesNoDecision",
    "Conditions": "IsAbleToReact(context.Observer) and Enemy(context.Source,context.Observer) and IsHit() and IsMeleeAttack() and not AnyEntityIsItem() and HasLastAttackTriggered()",
    "Properties": "UseSpell(SWAP,Target_SSTORM_SU_RadiantRetort,true,true,true)", "Cost": "ReactionActionPoint:1",
    "Stack": "SSTORM_SU_Radiance", "InterruptDefaultValue": "Ask;Enabled",
    "EnableCondition": "not HasStatus('SG_Incapacitated')", "EnableContext": "OnStatusApplied;OnStatusRemoved"})
P = "ClassLevelHigherOrEqualThan({},'Paladin')"
target("Target_SSTORM_SU_RadiantRetort", "Radiant Retort", "Radiant damage to a melee attacker.",
       "Action_Paladin_HealingRadiance",
       f"IF(not {P.format(11)}):DealDamage(5,Radiant,Magical);IF({P.format(11)} and not {P.format(17)}):DealDamage(10,Radiant,Magical);IF({P.format(17)}):DealDamage(15,Radiant,Magical)",
       "", "Character() and not Dead()", radius="3")
shout("Shout_SSTORM_SU_SolarFlare", "Solar Flare",
      "Channel Divinity. Emit a blinding flash: each enemy within 20 feet makes a Constitution saving throw or is blinded for 1 minute, repeating the save at the end of each of its turns.",
      "Action_Paladin_HealingRadiance", None, f"ActionPoint:1;{CD}", cond=ENEMIES, area="6",
      roll=SAVE("Constitution"), succ="ApplyStatus(SSTORM_SU_BLINDED,100,10)", save="Constitution")
status("SSTORM_SU_BLINDED", "Blinded by the Sun", "Blinded. Repeats the Constitution save at the end of each turn.",
       "Action_Paladin_HealingRadiance", None, using="BLINDED", TickType="EndTurn",
       RemoveConditions="SavingThrow(Ability.Constitution, SourceSpellDC())", RemoveEvents="OnTurn")
su_aura = aura("SU_WARMTH", "Sun's Warmth", "Aura (10 ft). You and allies within it have resistance to cold and fire damage.",
               "Action_Paladin_HealingRadiance", "Resistance(Cold, Resistant);Resistance(Fire, Resistant)")
passive("SSTORM_SU_IncandescentFury", "Incandescent Fury",
        "Your melee weapon attacks deal 1 extra radiant damage (approximating Improved Divine Smite's die becoming a d10).",
        "Action_Paladin_HealingRadiance", "IF(IsMeleeWeaponAttack()):CharacterWeaponDamage(1,Radiant)")
shout("Shout_SSTORM_SU_Zenith", "Zenith",
      "Fill yourself with the sun's wrath for 1 minute: cast Sunbeam without a spell slot, and at the start of each of your turns regain hit points equal to your Charisma modifier while at half health or below. Once per long rest.",
      "Action_Paladin_HealingRadiance", "ApplyStatus(SSTORM_SU_ZENITH,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_SU_ZENITH", "Zenith", "You can cast Sunbeam without a slot and regain hit points each turn while at half health or below.",
       "Action_Paladin_HealingRadiance", "UnlockSpell(Zone_SSTORM_SU_ZenithBeam)", TickType="StartTurn",
       TickFunctors="IF(HasHPPercentageLessThan(51)):RegainHitPoints(max(1,CharismaModifier))")
dn, dd = names("Zone_SSTORM_SU_ZenithBeam", "Sunbeam (Zenith)", "Cast Sunbeam without a spell slot.")
entry("Spell_Zone.txt", "Zone_SSTORM_SU_ZenithBeam", "SpellData",
      {"SpellType": "Zone", "Level": "", "UseCosts": "ActionPoint:1", "DisplayName": dn, "Description": dd},
      using="Zone_Sunbeam")
oath("OathOfTheSun", "Oath of the Sun",
     "A devotee of sunlight worship, bearing scorching rhetoric and spells. (Valda's Spire of Secrets)", {
         3: {"oath": ["Zone_BurningHands", "Projectile_GuidingBolt"],
             "spells": ["Shout_SSTORM_SU_GloriousRadiance", "Shout_SSTORM_SU_SolarFlare"]},
         5: {"oath": ["Target_Darkvision", "Projectile_ScorchingRay"]},
         7: {"spells": [su_aura]},
         9: {"oath": ["Target_Daylight", "Shout_SpiritGuardians"]},
         13: {"oath": ["Shout_FireShield", "Wall_WallOfFire"]},
         15: {"passives": ["SSTORM_SU_IncandescentFury"]},
         17: {"oath": ["Target_FlameStrike"]},
         20: {"spells": ["Shout_SSTORM_SU_Zenith"]},
     })

# ---------------------------------------------------------------- Oath of Winter
shout("Shout_SSTORM_WI_IceArmor", "Ice Armor",
      "Channel Divinity. As a bonus action, wreath your armor in ice: gain temporary hit points equal to twice your paladin level + your Charisma modifier.",
      "Spell_Evocation_ConeOfCold", "ApplyStatus(SSTORM_WI_ICE_ARMOR,100,600)", f"BonusActionPoint:1;{CD}")
status("SSTORM_WI_ICE_ARMOR", "Ice Armor", "Temporary hit points from a layer of protective ice.", "Spell_Evocation_ConeOfCold",
       "TemporaryHP(2*ClassLevel(Paladin)+CharismaModifier)", RemoveConditions="not HasTemporaryHP()", RemoveEvents="OnDamage")
dn, dd = names("Zone_SSTORM_WI_NorthWind", "North Wind",
               "Channel Divinity. Breathe a hoary wind in a 30-foot cone. Each creature makes a Constitution saving throw: 2d6 cold damage per point of your proficiency bonus and speed halved until your next turn on a failure, half damage on a success.")
entry("Spell_Zone.txt", "Zone_SSTORM_WI_NorthWind", "SpellData", {
    "SpellType": "Zone", "Level": "", "SpellSchool": "", "Range": "9", "Angle": "60",
    "SpellRoll": SAVE("Constitution"),
    "SpellSuccess": per_pb(2, "d6", "Cold") + ";ApplyStatus(SSTORM_WI_CHILLED,100,1)",
    "SpellFail": per_pb(2, "d6", "Cold", half=True), "TooltipAttackSave": "Constitution",
    "DisplayName": dn, "Description": dd, "UseCosts": f"ActionPoint:1;{CD}"}, using="Zone_ConeOfCold")
status("SSTORM_WI_CHILLED", "Chilled", "Speed halved.", "Spell_Evocation_ConeOfCold",
       "ActionResourceMultiplier(Movement,50,0)", negative=True)
wi_aura = aura("WI_FRIGID", "Frigid Aura", "Aura (10 ft). You and allies within it have resistance to cold and fire damage.",
               "Spell_Evocation_ConeOfCold", "Resistance(Cold, Resistant);Resistance(Fire, Resistant)")
passive("SSTORM_WI_Iceflesh", "Iceflesh",
        "When you're hit, use your reaction to freeze the blood in your veins: you take only half damage from that attack.",
        "Spell_Evocation_ConeOfCold", "UnlockInterrupt(Interrupt_SSTORM_WI_Iceflesh)")
self_hit_reaction("Interrupt_SSTORM_WI_Iceflesh", "Iceflesh", "Use your reaction to halve the damage of this hit.",
                  "Spell_Evocation_ConeOfCold", "ApplyStatus(OBSERVER_OBSERVER,SSTORM_WI_ICEFLESH,100,1)")
status("SSTORM_WI_ICEFLESH", "Iceflesh", "Damage taken is halved.", "Spell_Evocation_ConeOfCold",
       "DamageReduction(All,Half)", RemoveEvents="OnDamage")
shout("Shout_SSTORM_WI_FatherWinter", "Father Winter",
      "Become an effigy of Father Winter for 1 hour: immune to cold damage, creatures that damage you in melee take 2d10 cold damage, and enemies within 10 feet are slowed by frozen ground. Once per long rest.",
      "Spell_Evocation_ConeOfCold", "ApplyStatus(SSTORM_WI_FATHER_WINTER,100,600)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_WI_FATHER_WINTER", "Father Winter", "Immune to cold. Melee attackers take 2d10 cold damage. Enemies within 10 feet are slowed.",
       "Spell_Evocation_ConeOfCold", "Resistance(Cold, Immune)", AuraRadius="3",
       AuraStatuses="IF(Enemy()):ApplyStatus(SSTORM_VORTEX_SLOWED)")
passive("SSTORM_WI_FatherWinterRetort", "Father Winter: Frostbite",
        "While you are Father Winter, a creature that damages you with a melee attack takes 2d10 cold damage.",
        "Spell_Evocation_ConeOfCold", context="OnDamaged",
        conditions="HasStatus('SSTORM_WI_FATHER_WINTER',context.Target) and IsMeleeAttack()",
        functors="DealDamage(SWAP,2d10,Cold,Magical)")
oath("OathOfWinter", "Oath of Winter",
     "Keeper of a frigid oath, imbued with powers of elemental ice. (Valda's Spire of Secrets)", {
         3: {"oath": ["Target_FogCloud", "Target_CreateWater"],
             "spells": ["Shout_SSTORM_WI_IceArmor", "Zone_SSTORM_WI_NorthWind"]},
         5: {"oath": ["Target_HoldPerson", "Target_Shatter"]},
         7: {"spells": [wi_aura]},
         9: {"oath": ["Target_SleetStorm", "Target_Slow"]},
         13: {"oath": ["Shout_FireShield", "Target_IceStorm"]},
         15: {"passives": ["SSTORM_WI_Iceflesh"]},
         17: {"oath": ["Zone_ConeOfCold", "Target_HoldMonster"]},
         20: {"spells": ["Shout_SSTORM_WI_FatherWinter"], "passives": ["SSTORM_WI_FatherWinterRetort"]},
     })

# ---------------------------------------------------------------- write
for f, blocks in stats.items():
    if blocks:
        upsert_stats(f, blocks)
upsert_lsx(PUB / "ClassDescriptions" / "ClassDescriptions.lsx", classes)
upsert_lsx(PUB / "Progressions" / "Progressions.lsx", rows)
upsert_lsx(PUB / "Lists" / "SpellLists.lsx", lists)
upsert_lsx(PUB / "ActionResourceDefinitions" / "ActionResourceDefinitions.lsx", resources)
upsert_loca(loca)
print(f"OATHS_OK classes={len(classes)} rows={len(rows)} lists={len(lists)} "
      f"stats={sum(len(b) for b in stats.values())} loca={len(loca)}")
