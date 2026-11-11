"""Shared stats/progression builders for generators (used by gen_warden.py; gen_oaths.py has an older copy).

Call the builders to accumulate entries, then write(label) to upsert everything into the mod.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modlib import PUB, attr, handle, uid, upsert_lsx, upsert_loca, upsert_stats  # noqa: E402

SHOUT_ANIM = ("83fb0115-57dd-4cce-ac40-87182b2865e2,,;,,;eb4f3d5f-6815-4ad5-a5af-870942af0863,,;"
              "ba5068a2-ed31-4b9a-87cc-be28edb9ad25,,;42014429-21fb-412d-bba6-0f8216f5e502,,;,,;"
              "43fa5e31-ad7e-47a9-9ca2-f6d40ba8e1cf,,;,,;,,")
TARGET_ANIM = ("554a18f7-952e-494a-b301-7702a85d4bc9,,;,,;af94aac1-d8eb-4ccb-9520-694ade11b61c,,;"
               "f5db4001-b136-4c48-9aa4-026c4a7dd3b7,,;22dfbbf4-f417-4c84-b39e-2039315961e6,,;,,;"
               "5bfbe9f9-4fc3-4f26-b112-43d404db6a89,,;,,;,,")
PREP, CAST = "f719faf1-83e7-4407-a2f2-0880e26f9ca5", "a851aded-d542-482c-81ea-aa807d8b630f"
ENEMIES = "Enemy() and not Dead() and Character()"


def SAVE(ability, dc="SourceSpellDC()"):
    return f"not SavingThrow(Ability.{ability}, {dc})"


stats = {"Spell_Shout.txt": [], "Spell_Target.txt": [], "Spell_Zone.txt": [], "Spell_Projectile.txt": [], "Status_BOOST.txt": [],
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


def reaction(name, title, desc, icon, context, scope, conditions, props, cost="ReactionActionPoint:1", **extra):
    dn, dd = names(name, title, desc)
    entry("Interrupt.txt", name, "InterruptData", {
        "DisplayName": dn, "Description": dd, "Icon": icon, "InterruptContext": context,
        "InterruptContextScope": scope, "Container": "YesNoDecision", "Conditions": conditions,
        "Properties": props, "Cost": cost, "Stack": name, "InterruptDefaultValue": "Ask;Enabled",
        "EnableCondition": "not HasStatus('SG_Incapacitated')", "EnableContext": "OnStatusApplied;OnStatusRemoved", **extra})


def self_hit_reaction(name, title, desc, icon, props, cost="ReactionActionPoint:1", **extra):
    reaction(name, title, desc, icon, "OnPostRoll", "Self",
             "IsAbleToReact(context.Observer) and Self(context.Target,context.Observer) and "
             "HasDamageEffectFlag(DamageFlags.Hit) and not AnyEntityIsItem()", props, cost, **extra)


def self_aura(name, title, desc, icon, radius, aura_statuses, boosts=None, **extra):
    """A status carrying an aura (AuraRadius/AuraStatuses), as vanilla Aura of Protection does."""
    status(name, title, desc, icon, boosts, AuraRadius=radius, AuraStatuses=aura_statuses, **extra)


PB_TIERS = [(None, 4, 2), (4, 8, 3), (8, 12, 4), (12, 16, 5), (16, None, 6)]


def per_pb(dice_per_pb, die, dtype, half=False):
    """'N dice per point of proficiency bonus', as a chain of level-gated DealDamage functors."""
    out = []
    for lo, hi, pb in PB_TIERS:
        c = ([f"CharacterLevelGreaterThan({lo})"] if lo else []) + ([f"not CharacterLevelGreaterThan({hi})"] if hi else [])
        dmg = f"{dice_per_pb * pb}{die}"
        out.append(f"IF({' and '.join(c)}):DealDamage({'(' + dmg + ')/2' if half else dmg},{dtype},Magical)")
    return ";".join(out)


def resource(name, title, desc, replenish="Rest", dice=None):
    dn, dd = names("res:" + name, title, desc)
    x = (f'<attribute id="Description" type="TranslatedString" handle="{dd[:-2]}" version="1"/>'
         + (attr("DiceType", "uint32", dice) if dice else "")
         + f'<attribute id="DisplayName" type="TranslatedString" handle="{dn[:-2]}" version="1"/>'
         + attr("MaxLevel", "uint32", "0") + attr("Name", "FixedString", name)
         + attr("ReplenishType", "FixedString", replenish)
         + attr("ShowOnActionResourcePanel", "bool", "true") + attr("UUID", "guid", uid("res:" + name)))
    resources.append(f'<node id="ActionResourceDefinition">{x}</node>')


def spell_list(key, title, spells):
    u = uid("list:" + key)
    lists.append(f'<node id="SpellList">{attr("Name", "FixedString", title)}'
                 f'{attr("Spells", "LSString", ";".join(spells))}{attr("UUID", "guid", u)}</node>')
    return u


def subclass(parent, name, title, desc, levels, sound="Paladin", casting_ability="6", must_prepare="false",
             class_extra=""):
    """levels: {level: {"spells": [granted], "passives": [names], "boosts": str, "selectors": [raw]}}"""
    table = uid("table:" + name)
    for lvl, spec in sorted(levels.items()):
        sel = list(spec.get("selectors", []))
        if spec.get("spells"):
            u = spell_list(f"{name}:feat:{lvl}", f"{title} features level {lvl}", spec["spells"])
            sel.append(f"AddSpells({u},,{spec.get('ability', 'Charisma')},,AlwaysPrepared)")
        x = ((attr("Boosts", "LSString", spec["boosts"]) if spec.get("boosts") else "")
             + attr("Level", "uint8", lvl) + attr("Name", "LSString", name)
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
                   + attr("LearningStrategy", "uint8", "1") + attr("MustPrepareSpells", "bool", must_prepare)
                   + attr("Name", "FixedString", name) + attr("ParentGuid", "guid", parent)
                   + attr("PrimaryAbility", "uint8", "1") + attr("ProgressionTableUUID", "guid", table)
                   + attr("SoundClassType", "FixedString", sound) + attr("SpellCastingAbility", "uint8", casting_ability)
                   + class_extra + attr("UUID", "guid", uid("class:" + name)) + "</node>")
    return uid("class:" + name)


def write(label):
    for f, blocks in stats.items():
        if blocks:
            upsert_stats(f, blocks)
    upsert_lsx(PUB / "ClassDescriptions" / "ClassDescriptions.lsx", classes)
    upsert_lsx(PUB / "Progressions" / "Progressions.lsx", rows)
    upsert_lsx(PUB / "Lists" / "SpellLists.lsx", lists)
    if resources:
        upsert_lsx(PUB / "ActionResourceDefinitions" / "ActionResourceDefinitions.lsx", resources)
    upsert_loca(loca)
    print(f"{label}_OK classes={len(classes)} rows={len(rows)} lists={len(lists)} "
          f"stats={sum(len(b) for b in stats.values())} loca={len(loca)}")
