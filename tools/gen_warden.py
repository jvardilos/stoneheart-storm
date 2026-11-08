#!/usr/bin/env python3
"""Generate the Warden's Champion's Calls from Valda's Spire of Secrets.

New calls: Bloodwrath Guardian, Grey Watchman, Nightgaunt, Soulblood Shaman, Storm Sentinel,
Verdant Protector (features at Warden 3/6/13/20). Also: Stoneheart Defender 13/20, a reworked
Warden's Mark (Predator's Scent / Green Mark hooks), the Warden subclass list, and a Warden
multiclass level-1 row. Levels 13+ need a level-cap mod.

Run: python3 -I tools/gen_warden.py   (then ./build.sh)
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_common import (ENEMIES, SAVE, TARGET_ANIM, entry, names, passive, reaction, resource, rows,  # noqa: E402
                        shout, spell_list, status, subclass, target, write, self_aura)
from modlib import PUB, attr, uid  # noqa: E402

WARDEN = "060452bd-db39-4f43-b6b4-c9debcd5199e"
WARDEN_L1_ROW = "9def7643-cd45-4149-ae83-9dd230094175"
STONEHEART = "d8160ab6-c03e-4d80-a3d6-c5dc159f4d40"
STONEHEART_TABLE = "3d220ff8-279b-43bd-87b3-c930d957b08b"
MARK = "SSTORM_WARDENS_MARK"
GRASPS = "SpellId('Shout_SSTORM_WardensGrasp') or SpellId('Shout_SSTORM_Earthshatter')"
ICON_MARK = "Spell_Enchantment_CompelledDuel"
ICON_DEF = "PassiveFeature_MultiattackDefense"
ICON_STORM = "Spell_Evocation_LightningBolt"
ICON_DARK = "Spell_Evocation_Darkness"
ICON_GREEN = "Action_Paladin_HealingRadiance"


def on_grasp_aura(passive_name, title, desc, icon, aura_status, radius, aura_statuses):
    """Passive: when you use Warden's Grasp/Earthshatter, gain a 1-turn aura status."""
    passive(passive_name, title, desc, icon, context="OnCast", conditions=GRASPS,
            functors=f"ApplyStatus(SELF,{aura_status},100,1)")
    self_aura(aura_status, title, desc, icon, radius, aura_statuses)


# ------------------------------------------------------------- shared pieces
passive("SSTORM_Mettle", "Mettle",
        "Your determination lets you shrug off effects: you have advantage on Constitution saving throws "
        "(approximating 'no damage on a successful Constitution save for half').", ICON_DEF,
        "Advantage(SavingThrow, Constitution)")

# Warden's Mark, now owned by this generator (adds Predator's Scent and Green Mark hooks)
dn, dd = names("Target_SSTORM_WardensMark", "Warden's Mark",
               "Mark a creature you can see within 30 feet. While it is within 5 feet of you, it has disadvantage on attack rolls that don't target you. Lasts 1 minute or until you mark another creature.")
HP = "HasPassive('{}',context.Source)"
entry("Spell_Target.txt", "Target_SSTORM_WardensMark", "SpellData", {
    "SpellType": "Target",
    "SpellProperties": ";".join([
        f"IF(not {HP.format('SSTORM_BG_PredatorsScent')}):ApplyStatus({MARK},100,10)",
        f"IF({HP.format('SSTORM_BG_PredatorsScent')}):ApplyStatus({MARK},100,100)",
        f"IF({HP.format('SSTORM_MarkImprovement')}):ApplyStatus(SELF,SSTORM_MARK_EXTRA_ATTACK,100,10)",
        f"IF({HP.format('SSTORM_VP_GreenMark')}):ApplyStatus(SSTORM_VP_ENTANGLED,100,10)"]),
    "TargetRadius": "9", "TargetConditions": "Character() and not Dead() and not Ally() and not Self()",
    "Icon": ICON_MARK, "DisplayName": "hSSTORMmarkNAME;1", "Description": "hSSTORMmarkDESC;1",
    "TooltipStatusApply": f"ApplyStatus({MARK},100,10)", "CastTextEvent": "Cast", "UseCosts": "BonusActionPoint:1",
    "SpellAnimation": TARGET_ANIM, "VerbalIntent": "Control", "SpellStyleGroup": "Class",
    "SpellFlags": "HasHighGroundRangeExtension;RangeIgnoreVerticalThreshold;IsHarmful"})

# ------------------------------------------------------------- Bloodwrath Guardian
TRANCE = ("Advantage(Ability, Strength);Advantage(SavingThrow, Strength);ActionResource(Movement,3,0);"
          f"IF(HasStatus('{MARK}',context.Target) and IsMeleeWeaponAttack()):Advantage(AttackRoll);Advantage(AttackTarget)")
shout("Shout_SSTORM_BG_FeralTrance", "Feral Trance",
      "Bonus action. Fall into a primal battle trance for 1 minute: advantage on Strength checks and saves, +10 ft speed, advantage on melee weapon attacks against a creature you've marked, but attack rolls against you have advantage. Once per short rest.",
      ICON_MARK, "ApplyStatus(SSTORM_BG_TRANCE,100,10)", "BonusActionPoint:1", cooldown="OncePerShortRest")
status("SSTORM_BG_TRANCE", "Feral Trance", "Advantage on Strength checks and saves, +10 ft speed, advantage on melee attacks against your mark; attacks against you have advantage.",
       ICON_MARK, TRANCE)
passive("SSTORM_BG_PredatorsScent", "Predator's Scent",
        "Your Warden's Mark lasts far longer (until you mark another creature), and you have advantage on Survival checks.",
        ICON_MARK, "Advantage(Skill, Survival)")
shout("Shout_SSTORM_BG_PrimalBeast", "Form of the Primal Beast",
      "Become an echo of the Primal Beast for 1 minute: you gain the benefits of Feral Trance and 40 temporary hit points, and your melee weapon hits give targets a bleeding wound (1d8 damage at the start of each of their turns; constructs, oozes and undead are immune). Once per long rest.",
      ICON_MARK, "ApplyStatus(SSTORM_BG_BEAST,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_BG_BEAST", "Form of the Primal Beast", "Feral Trance benefits, 40 temporary hit points, and bleeding wounds on melee hits.",
       ICON_MARK, TRANCE + ";TemporaryHP(40)")
passive("SSTORM_BG_BleedingWounds", "Primal Beast: Bleeding Wounds",
        "While in the Form of the Primal Beast, your melee weapon hits inflict a bleeding wound.", ICON_MARK,
        context="OnDamage",
        conditions="HasStatus('SSTORM_BG_BEAST',context.Source) and IsMeleeWeaponAttack() and not Tagged('UNDEAD') and not Tagged('CONSTRUCT') and not Tagged('OOZE')",
        functors="ApplyStatus(SSTORM_BG_BLEEDING,100,10)")
status("SSTORM_BG_BLEEDING", "Bleeding Wound", "Takes 1d8 damage at the start of each turn.", ICON_MARK, None,
       negative=True, TickType="StartTurn", TickFunctors="DealDamage(1d8,Slashing)")
subclass(WARDEN, "BloodwrathGuardian", "Bloodwrath Guardian",
         "Enters a trance to channel the primal ferocity of beasts. (Valda's Spire of Secrets)", {
             3: {"spells": ["Shout_SSTORM_BG_FeralTrance"]},
             6: {"passives": ["SSTORM_BG_PredatorsScent"]},
             13: {"passives": ["Evasion"]},
             20: {"spells": ["Shout_SSTORM_BG_PrimalBeast"], "passives": ["SSTORM_BG_BleedingWounds"]},
         })

# ------------------------------------------------------------- Grey Watchman
DIE = "SuperiorityDie:1"
target("Target_SSTORM_GW_BullRush", "Bull Rush",
       "Maneuver. Bonus action: expend a battle die and shove a creature, knocking it prone on a success.",
       None, None, f"BonusActionPoint:1;{DIE}", None, using="Target_Shove", radius=None,
       SpellSuccess="IF(not Ally()):ApplyStatus(PRONE,100,1)")
target("Target_SSTORM_GW_Bulwark", "Bulwark",
       "Maneuver. Bonus action: expend a battle die to brace against a creature's counterattack. The next damage you take before your next turn is reduced by 5.",
       ICON_DEF, "ApplyStatus(SELF,SSTORM_GW_BULWARK,100,1)", f"BonusActionPoint:1;{DIE}",
       "Enemy() and not Dead() and Character()", radius="1.5")
status("SSTORM_GW_BULWARK", "Bulwark", "The next damage you take is reduced by 5.", ICON_DEF,
       "DamageReduction(All,Flat,5)", RemoveEvents="OnDamage")
shout("Shout_SSTORM_GW_RecklessAssault", "Reckless Assault",
      "Maneuver. Expend a battle die (no action): advantage on your attack rolls this turn, but attack rolls against you have advantage until the start of your next turn.",
      ICON_MARK, "ApplyStatus(SSTORM_GW_RECKLESS,100,1)", DIE)
status("SSTORM_GW_RECKLESS", "Reckless Assault", "Advantage on attacks; attacks against you have advantage.",
       ICON_MARK, "Advantage(AttackRoll);Advantage(AttackTarget)")
target("Target_SSTORM_GW_StaggeringStrike", "Staggering Strike",
       "Maneuver. Bonus action: expend a battle die and strike. On a hit against a humanoid, it must make a Constitution saving throw or be incapacitated until the start of your next turn.",
       ICON_MARK, None, f"BonusActionPoint:1;{DIE}", None, using="Target_AdvancedMeleeWeaponAction", radius=None,
       SpellSuccess="DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);"
                    "IF(Tagged('HUMANOID') and not SavingThrow(Ability.Constitution, ManeuverSaveDC())):ApplyStatus(SSTORM_GW_STAGGERED,100,1)",
       TooltipAttackSave="MeleeWeaponAttack;Constitution")
status("SSTORM_GW_STAGGERED", "Staggered", "Incapacitated: can't take actions, bonus actions or reactions.", ICON_MARK,
       "ActionResourceBlock(ActionPoint);ActionResourceBlock(BonusActionPoint);ActionResourceBlock(ReactionActionPoint)",
       negative=True)
on_grasp_aura("SSTORM_GW_HoldTheLine", "Hold the Line",
              "When you use Warden's Grasp, allies within 5 feet gain +1 AC and +1 to saving throws until the start of your next turn.",
              ICON_DEF, "SSTORM_GW_HOLD_AURA", "1.5",
              "IF(Ally() and not Self() and not Tagged('INANIMATE')):ApplyStatus(SSTORM_GW_HOLD_BUFF)")
status("SSTORM_GW_HOLD_BUFF", "Hold the Line", "+1 AC and +1 to saving throws.", ICON_DEF, "AC(1);RollBonus(SavingThrow,1)")
passive("SSTORM_GW_FortificationExpert", "Fortification Expert",
        "Your experience manning battlements gives you advantage on Athletics and Investigation checks.", ICON_DEF,
        "Advantage(Skill, Athletics);Advantage(Skill, Investigation)")
shout("Shout_SSTORM_GW_UnbreakableSentinel", "Unbreakable Sentinel",
      "Become a paragon of battle for 1 minute: +2 AC, an additional reaction each round, and hitting a creature you've marked restores a battle die. Once per long rest.",
      ICON_DEF, "ApplyStatus(SSTORM_GW_UNBREAKABLE,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_GW_UNBREAKABLE", "Unbreakable Sentinel", "+2 AC and an extra reaction; hitting your mark restores a battle die.",
       ICON_DEF, "AC(2);ActionResource(ReactionActionPoint,1,0)")
passive("SSTORM_GW_UnbreakableRegain", "Unbreakable Sentinel: Second Wind",
        "While Unbreakable Sentinel is active, hitting a creature you've marked restores a battle die.", ICON_DEF,
        context="OnDamage", conditions=f"HasStatus('SSTORM_GW_UNBREAKABLE',context.Source) and HasStatus('{MARK}',context.Target)",
        functors="RestoreResource(SELF,SuperiorityDie,1,0)")
subclass(WARDEN, "GreyWatchman", "Grey Watchman",
         "A maneuver-trained guard that repels invaders from cities. (Valda's Spire of Secrets)", {
             3: {"spells": ["Target_SSTORM_GW_BullRush", "Target_SSTORM_GW_Bulwark", "Shout_SSTORM_GW_RecklessAssault",
                            "Target_SSTORM_GW_StaggeringStrike"],
                 "passives": ["SSTORM_GW_HoldTheLine"], "boosts": "ActionResource(SuperiorityDie,2,0)"},
             6: {"passives": ["SSTORM_GW_FortificationExpert"]},
             7: {"boosts": "ActionResource(SuperiorityDie,1,0)"},
             13: {"passives": ["SSTORM_Mettle"]},
             19: {"boosts": "ActionResource(SuperiorityDie,1,0)"},
             20: {"spells": ["Shout_SSTORM_GW_UnbreakableSentinel"], "passives": ["SSTORM_GW_UnbreakableRegain"]},
         })

# ------------------------------------------------------------- Nightgaunt
passive("SSTORM_NG_Darkvision", "Nightgaunt Darkvision", "You can see in darkness within 60 feet.", ICON_DARK,
        "DarkvisionRangeMin(18)")
passive("SSTORM_NG_MarkedForDeath", "Marked for Death",
        "Your mark beckons death: when your melee weapon hit leaves a creature you've marked at 20% of its hit points or fewer, it drops to 0 hit points instead (approximating 'if its remaining hit points are lower than the damage you dealt').",
        ICON_DARK, context="OnDamage",
        conditions=f"HasStatus('{MARK}',context.Target) and IsMeleeWeaponAttack() and HasHPPercentageLessThan(21)",
        functors="Kill()")
passive("SSTORM_NG_UndeadEmpathy", "Undead Empathy",
        "Undead struggle to strike you: they have disadvantage on attack rolls against you.", ICON_DARK,
        "Disadvantage(AttackTarget,UNDEAD)")
shout("Shout_SSTORM_NG_Gravelord", "Gravelord",
      "Divorce yourself from life for 1 minute: immune to poison damage and the poisoned condition, and once per turn your melee weapon hits deal an extra 4d6 necrotic damage and grant you temporary hit points. Once per long rest.",
      ICON_DARK, "ApplyStatus(SSTORM_NG_GRAVELORD,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_NG_GRAVELORD", "Gravelord", "Immune to poison; melee hits deal extra necrotic damage once per turn.",
       ICON_DARK, "Resistance(Poison, Immune);StatusImmunity(SG_Poisoned)")
passive("SSTORM_NG_GravelordStrike", "Gravelord: Necrotic Strike",
        "Once per turn while Gravelord is active, a melee weapon hit deals an extra 4d6 necrotic damage and gives you 14 temporary hit points.",
        ICON_DARK, context="OnDamage", props="OncePerTurn;Highlighted",
        conditions="HasStatus('SSTORM_NG_GRAVELORD',context.Source) and IsMeleeWeaponAttack()",
        functors="DealDamage(4d6,Necrotic,Magical);ApplyStatus(SELF,SSTORM_NG_GRAVE_THP,100,1)")
status("SSTORM_NG_GRAVE_THP", "Grave Vigor", "Temporary hit points from Gravelord.", ICON_DARK, "TemporaryHP(14)")
subclass(WARDEN, "Nightgaunt", "Nightgaunt",
         "An ally of the undead, suffused with necromantic energies. (Valda's Spire of Secrets)", {
             3: {"passives": ["SSTORM_NG_Darkvision", "SSTORM_NG_MarkedForDeath"]},
             6: {"passives": ["SSTORM_NG_UndeadEmpathy"]},
             13: {"passives": ["Evasion"]},
             20: {"spells": ["Shout_SSTORM_NG_Gravelord"], "passives": ["SSTORM_NG_GravelordStrike"]},
         })

# ------------------------------------------------------------- Soulblood Shaman (Wisdom third-caster, druid list)
CANTRIPS = "b8faf12f-ca42-45c0-84f8-6951b526182a"   # vanilla Druid Cantrips
DRUID = {1: "2cd54137-2fe5-4100-aad3-df64735a8145", 2: "92126d17-7f1a-41d2-ae6c-a8d254d2b135",
         3: "3156daf5-9266-41d0-b52c-5bc559a98654", 4: "09c326c9-672c-4198-a4c0-6f07323bde27"}


def vanilla_list(u):
    for f in (PUB.parent.parent / ".cache").rglob("SpellLists.lsx"):
        for n in ET.parse(f).getroot().iter("node"):
            a = {x.get("id"): x.get("value") for x in n.findall("attribute")}
            if a.get("UUID") == u:
                return [s for s in a.get("Spells", "").split(";") if s]
    raise SystemExit(f"vanilla spell list {u} not in .cache")


combined, upto = [], {}
for lvl in (1, 2, 3, 4):
    combined += [s for s in vanilla_list(DRUID[lvl]) if s not in combined]
    upto[lvl] = spell_list(f"Soulblood:upto{lvl}", f"Soulblood Shaman druid spells up to level {lvl}", combined)
SEL = "SSTORMSoulblood"
pick = lambda tier, n: f"SelectSpells({upto[tier]},{n},0,{SEL})"  # noqa: E731
slots = lambda *pairs: ";".join(f"ActionResource(SpellSlot,{n},{lv})" for n, lv in pairs)  # noqa: E731
passive("SSTORM_SB_Whispers", "Whispers of Beyond",
        "Ancestor spirits guide you: advantage on History, Religion and Insight checks.", ICON_GREEN,
        "Advantage(Skill, History);Advantage(Skill, Religion);Advantage(Skill, Insight)")
passive("SSTORM_SB_Soulblood", "Soulblood",
        "When a creature within 5 feet damages you, you can use your reaction to mark it.", ICON_MARK,
        "UnlockInterrupt(Interrupt_SSTORM_SB_Soulblood)")
reaction("Interrupt_SSTORM_SB_Soulblood", "Soulblood", "Use your reaction to mark the creature that damaged you.",
         ICON_MARK, "OnCastHit", "Self",
         "IsAbleToReact(context.Observer) and Enemy(context.Source,context.Observer) and IsHit() and not AnyEntityIsItem() "
         "and HasLastAttackTriggered() and not DistanceToEntityGreaterThan(2, context.ObserverPosition, context.Source)",
         f"ApplyStatus(OBSERVER_SOURCE,{MARK},100,10)")
shout("Shout_SSTORM_SB_EtherealWatcher", "Ethereal Watcher",
      "Shrug off your mortal form for 1 minute: gain an extra 1st- and 2nd-level spell slot, and as a bonus action you can tear yourself back through the planes, dealing 4d6 force damage to enemies within 10 feet. Once per long rest.",
      ICON_GREEN, "ApplyStatus(SSTORM_SB_ETHEREAL,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_SB_ETHEREAL", "Ethereal Watcher", "Extra spell slots; you can release a burst of force as a bonus action.",
       ICON_GREEN, "ActionResource(SpellSlot,1,1);ActionResource(SpellSlot,1,2);UnlockSpell(Shout_SSTORM_SB_EtherealBurst)")
shout("Shout_SSTORM_SB_EtherealBurst", "Ethereal Return",
      "Bonus action. Each enemy within 10 feet is pulled partially between the planes and takes 4d6 force damage.",
      ICON_GREEN, "DealDamage(4d6,Force,Magical)", "BonusActionPoint:1", cond=ENEMIES, area="3")
subclass(WARDEN, "SoulbloodShaman", "Soulblood Shaman",
         "Manipulates their own soul to conjure long-forgotten magic. Casts druid spells with Wisdom. (Valda's Spire of Secrets)", {
             3: {"boosts": slots((2, 1)), "passives": ["UnlockedSpellSlotLevel1", "SSTORM_SB_Soulblood"],
                 "selectors": [f"SelectSpells({CANTRIPS},2,0,,,,AlwaysPrepared)", pick(1, 3)]},
             4: {"boosts": slots((1, 1)), "selectors": [pick(1, 1)]},
             6: {"passives": ["SSTORM_SB_Whispers"]},
             7: {"boosts": slots((1, 1), (2, 2)), "passives": ["UnlockedSpellSlotLevel2"], "selectors": [pick(2, 1)]},
             8: {"selectors": [pick(2, 1)]},
             10: {"boosts": slots((1, 2)), "selectors": [f"SelectSpells({CANTRIPS},1,0,,,,AlwaysPrepared)", pick(2, 1)]},
             11: {"selectors": [pick(2, 1)]},
             13: {"boosts": slots((2, 3)), "passives": ["UnlockedSpellSlotLevel3", "MagicResistance"], "selectors": [pick(3, 1)]},
             14: {"selectors": [pick(3, 1)]},
             16: {"boosts": slots((1, 3)), "selectors": [pick(3, 1)]},
             19: {"boosts": slots((1, 4)), "selectors": [pick(4, 1)]},
             20: {"spells": ["Shout_SSTORM_SB_EtherealWatcher"], "selectors": [pick(4, 1)]},
         }, casting_ability="5",
         class_extra=attr("MulticlassSpellcasterModifier", "double", "0.34") + attr("SpellList", "guid", upto[4]))

# ------------------------------------------------------------- Storm Sentinel
passive("SSTORM_SS_Thunderblast", "Thunderblast",
        "When you hit a creature you've marked with a melee weapon attack, lightning arcs to its allies within 5 feet, dealing 1d8 lightning damage to each.",
        ICON_STORM, context="OnDamage", conditions=f"HasStatus('{MARK}',context.Target) and IsMeleeWeaponAttack()",
        functors="ApplyStatus(SSTORM_SS_ARC_SOURCE,100,1)")
self_aura("SSTORM_SS_ARC_SOURCE", "Thunderblast", "Lightning arcs from this creature.", ICON_STORM, "1.5",
          "IF(Ally() and not Self()):ApplyStatus(SSTORM_SS_ARCED)", negative=True)
status("SSTORM_SS_ARCED", "Thunderblast", "Struck by arcing lightning.", ICON_STORM, None, negative=True,
       OnApplyFunctors="DealDamage(1d8,Lightning,Magical)")
on_grasp_aura("SSTORM_SS_StaticBurst", "Static Burst",
              "When you use Warden's Grasp, enemies within 5 feet can't take reactions until the start of your next turn.",
              ICON_STORM, "SSTORM_SS_STATIC_AURA", "1.5", "IF(Enemy()):ApplyStatus(SSTORM_SS_STATIC)")
status("SSTORM_SS_STATIC", "Static Burst", "Can't take reactions.", ICON_STORM,
       "ActionResourceBlock(ReactionActionPoint)", negative=True)
passive("SSTORM_SS_StormlordFlight", "Stormlord", "You have a flying speed.", ICON_STORM, "UnlockSpell(Projectile_Fly_Spell)")
shout("Shout_SSTORM_SS_Stormlord", "Stormlord",
      "Call a bolt of lightning down upon yourself for 1 minute: cast Call Lightning as a bonus action without a spell slot, and call down its bolts as a bonus action on later turns. Once per long rest.",
      ICON_STORM, "ApplyStatus(SSTORM_SS_STORMLORD,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_SS_STORMLORD", "Stormlord", "Cast Call Lightning and its bolts as bonus actions without a slot.",
       ICON_STORM, "UnlockSpell(Target_SSTORM_SS_CallLightning);UnlockSpell(Target_SSTORM_SS_Bolt)")
target("Target_SSTORM_SS_CallLightning", "Call Lightning (Stormlord)", "Call Lightning as a bonus action without a spell slot.",
       None, None, "BonusActionPoint:1", None, using="Target_CallLightning", radius=None)
target("Target_SSTORM_SS_Bolt", "Lightning Bolt (Stormlord)", "Call down another bolt as a bonus action.",
       None, None, "BonusActionPoint:1", None, using="Target_CallLightning_LightningBolt", radius=None,
       RequirementConditions="HasStatus('CALL_LIGHTNING_TECHNICAL')")
subclass(WARDEN, "StormSentinel", "Storm Sentinel",
         "Channels the fury of thunderstorms to protect the weak. (Valda's Spire of Secrets)", {
             3: {"passives": ["SSTORM_SS_Thunderblast"]},
             6: {"passives": ["SSTORM_SS_StaticBurst"]},
             13: {"passives": ["Evasion"]},
             20: {"spells": ["Shout_SSTORM_SS_Stormlord"], "passives": ["SSTORM_SS_StormlordFlight"]},
         })

# ------------------------------------------------------------- Verdant Protector
passive("SSTORM_VP_GreenMark", "Green Mark",
        "When you mark a creature, plants rise to hinder it: its movement is halved while the mark lasts.", ICON_GREEN)
status("SSTORM_VP_ENTANGLED", "Green Mark", "The ground hinders its movement: speed halved.", ICON_GREEN,
       "ActionResourceMultiplier(Movement,50,0)", negative=True)
passive("SSTORM_VP_VerdantSkin", "Verdant Skin", "You are proficient in Stealth.", ICON_GREEN,
        "ProficiencyBonus(Skill, Stealth)")
shout("Shout_SSTORM_VP_VerdantSkin", "Verdant Skin",
      "Draw vines and leaves around you: advantage on Stealth checks until you move.", ICON_GREEN,
      "ApplyStatus(SSTORM_VP_CONCEALED,100,-1)", "ActionPoint:1")
status("SSTORM_VP_CONCEALED", "Verdant Skin", "Advantage on Stealth checks until you move.", ICON_GREEN,
       "Advantage(Skill, Stealth)", RemoveEvents="OnMove")
shout("Shout_SSTORM_VP_OakSentinel", "Form of the Oak Sentinel",
      "Transform into a bark-covered titan for 1 minute: your Armor Class becomes 20. Once per long rest.",
      ICON_GREEN, "ApplyStatus(SSTORM_VP_OAK,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_VP_OAK", "Form of the Oak Sentinel", "Armor Class 20.", ICON_GREEN, "ACOverrideFormula(20,false)")
subclass(WARDEN, "VerdantProtector", "Verdant Protector",
         "Imbued with the power of the forests and pledged to defend them. (Valda's Spire of Secrets)", {
             3: {"passives": ["SSTORM_VP_GreenMark"]},
             6: {"spells": ["Shout_SSTORM_VP_VerdantSkin"], "passives": ["SSTORM_VP_VerdantSkin"]},
             13: {"passives": ["SSTORM_Mettle"]},
             20: {"spells": ["Shout_SSTORM_VP_OakSentinel"]},
         })

# ------------------------------------------------------------- Stoneheart Defender 13 / 20
shout("Shout_SSTORM_SH_ImmortalMountain", "Immortal Mountain",
      "Encase yourself in stone for 1 minute: bludgeoning, piercing and slashing damage you take is reduced by 5, and you keep the benefits of Roots of Rock the whole time. Once per long rest.",
      ICON_DEF, "ApplyStatus(SSTORM_SH_MOUNTAIN,100,10)", "ActionPoint:1", cooldown="OncePerRest")
status("SSTORM_SH_MOUNTAIN", "Immortal Mountain", "Physical damage reduced by 5; Roots of Rock for the duration.", ICON_DEF,
       "DamageReduction(Bludgeoning,Flat,5);DamageReduction(Piercing,Flat,5);DamageReduction(Slashing,Flat,5)",
       TickType="StartTurn", TickFunctors="ApplyStatus(SSTORM_ROOTS_OF_ROCK,100,1)",
       OnApplyFunctors="ApplyStatus(SSTORM_ROOTS_OF_ROCK,100,1)")
sh_list = spell_list("StoneheartDefender:feat:20", "Stoneheart Defender features level 20", ["Shout_SSTORM_SH_ImmortalMountain"])
for lvl, extra in [(13, attr("PassivesAdded", "LSString", "SSTORM_Mettle")),
                   (20, attr("Selectors", "LSString", f"AddSpells({sh_list},,Charisma,,AlwaysPrepared)"))]:
    rows.append('<node id="Progression">' + attr("Level", "uint8", lvl) + attr("Name", "LSString", "StoneheartDefender")
                + extra + attr("ProgressionType", "uint8", "1") + attr("TableUUID", "guid", STONEHEART_TABLE)
                + attr("UUID", "guid", uid(f"row:StoneheartDefender:{lvl}")) + "</node>")

write("WARDEN")

# ------------------------------------------------------------- Warden subclass list + multiclass row
CALLS = [STONEHEART] + [uid("class:" + n) for n in
                        ["BloodwrathGuardian", "GreyWatchman", "Nightgaunt", "SoulbloodShaman", "StormSentinel", "VerdantProtector"]]
path = PUB / "Progressions" / "Progressions.lsx"
tree = ET.parse(path)
children = tree.getroot().find("region").find("node").find("children")


def row_attrs(n):
    return {a.get("id"): a for a in n.findall("attribute")}


l1 = next(n for n in children if row_attrs(n).get("UUID") is not None and row_attrs(n)["UUID"].get("value") == WARDEN_L1_ROW)


def set_subclasses(node):
    for old in node.findall("children"):
        node.remove(old)
    ch = ET.SubElement(node, "children")
    sc = ET.SubElement(ET.SubElement(ch, "node", {"id": "SubClasses"}), "children")
    for u in CALLS:
        ET.SubElement(ET.SubElement(sc, "node", {"id": "SubClass"}), "attribute", {"id": "Object", "type": "guid", "value": u})


set_subclasses(l1)
mc_uuid = uid("row:Warden:1:multiclass")
for n in list(children):
    a = row_attrs(n)
    if a.get("UUID") is not None and a["UUID"].get("value") == mc_uuid:
        children.remove(n)
la = row_attrs(l1)
mc = ET.SubElement(children, "node", {"id": "Progression"})
mc_attrs = [("Boosts", "LSString", "Proficiency(LightArmor);Proficiency(MediumArmor);Proficiency(Shields);"
             "Proficiency(SimpleWeapons);Proficiency(MartialWeapons)"),
            ("IsMulticlass", "bool", "true"), ("Level", "uint8", "1"), ("Name", "LSString", "Warden")]
if "PassivesAdded" in la:
    mc_attrs.append(("PassivesAdded", "LSString", la["PassivesAdded"].get("value")))
mc_attrs += [("ProgressionType", "uint8", "0"),
             ("Selectors", "LSString", ";".join(s for s in la["Selectors"].get("value").split(";") if not s.startswith("SelectSkills"))),
             ("TableUUID", "guid", la["TableUUID"].get("value")), ("UUID", "guid", mc_uuid)]
for i, t, v in mc_attrs:
    ET.SubElement(mc, "attribute", {"id": i, "type": t, "value": v})
set_subclasses(mc)
ET.indent(tree, space="    ")
tree.write(path, encoding="UTF-8", xml_declaration=True)

# verify subclass lists
check = ET.parse(path).getroot().find("region").find("node").find("children")
for u in (WARDEN_L1_ROW, mc_uuid):
    n = next(n for n in check if row_attrs(n).get("UUID") is not None and row_attrs(n)["UUID"].get("value") == u)
    got = [s.get("value") for s in n.iter("attribute") if s.get("id") == "Object"]
    if got != CALLS:
        raise SystemExit(f"FAIL subclass list on {u}: {got}")
print(f"WARDEN_SUBCLASSES_OK {len(CALLS)} calls on L1 + multiclass rows")
