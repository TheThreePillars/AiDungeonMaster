"""Bestiary module containing monster definitions for Pathfinder 1e."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MonsterType(Enum):
    """Monster type categories."""
    ABERRATION = "Aberration"
    ANIMAL = "Animal"
    CONSTRUCT = "Construct"
    DRAGON = "Dragon"
    FEY = "Fey"
    HUMANOID = "Humanoid"
    MAGICAL_BEAST = "Magical Beast"
    MONSTROUS_HUMANOID = "Monstrous Humanoid"
    OOZE = "Ooze"
    OUTSIDER = "Outsider"
    PLANT = "Plant"
    UNDEAD = "Undead"
    VERMIN = "Vermin"


class Size(Enum):
    """Creature size categories."""
    FINE = "Fine"
    DIMINUTIVE = "Diminutive"
    TINY = "Tiny"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    HUGE = "Huge"
    GARGANTUAN = "Gargantuan"
    COLOSSAL = "Colossal"


SIZE_MODIFIERS = {
    Size.FINE: 8,
    Size.DIMINUTIVE: 4,
    Size.TINY: 2,
    Size.SMALL: 1,
    Size.MEDIUM: 0,
    Size.LARGE: -1,
    Size.HUGE: -2,
    Size.GARGANTUAN: -4,
    Size.COLOSSAL: -8,
}


@dataclass
class Attack:
    """Represents a monster attack."""
    name: str
    attack_bonus: int
    damage_dice: str
    damage_bonus: int = 0
    damage_type: str = "slashing"
    special: str = ""


@dataclass
class SpecialAbility:
    """Represents a special ability."""
    name: str
    description: str
    ability_type: str = "Ex"  # Ex, Su, Sp


@dataclass
class Monster:
    """Represents a monster from the bestiary."""
    name: str
    monster_type: MonsterType
    size: Size
    challenge_rating: float
    hit_dice: str
    hp: int
    armor_class: int
    touch_ac: int
    flat_footed_ac: int
    speed: int = 30

    # Ability scores
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Saves
    fortitude: int = 0
    reflex: int = 0
    will: int = 0

    # Combat
    base_attack_bonus: int = 0
    cmb: int = 0
    cmd: int = 10
    initiative: int = 0

    # Attacks
    attacks: list[Attack] = field(default_factory=list)

    # Special abilities
    special_abilities: list[SpecialAbility] = field(default_factory=list)

    # Immunities and resistances
    damage_reduction: str = ""
    immunities: list[str] = field(default_factory=list)
    resistances: dict[str, int] = field(default_factory=dict)
    spell_resistance: int = 0

    # Senses
    darkvision: int = 0
    low_light_vision: bool = False
    scent: bool = False
    blindsense: int = 0

    # Skills and feats
    skills: dict[str, int] = field(default_factory=dict)
    feats: list[str] = field(default_factory=list)

    # Descriptive
    description: str = ""
    environment: str = ""
    organization: str = ""
    treasure: str = "standard"

    # Subtypes
    subtypes: list[str] = field(default_factory=list)
    alignment: str = "N"

    def get_xp_reward(self) -> int:
        """Calculate XP reward based on CR."""
        xp_by_cr = {
            0.125: 50, 0.25: 100, 0.33: 135, 0.5: 200,
            1: 400, 2: 600, 3: 800, 4: 1200, 5: 1600,
            6: 2400, 7: 3200, 8: 4800, 9: 6400, 10: 9600,
            11: 12800, 12: 19200, 13: 25600, 14: 38400,
            15: 51200, 16: 76800, 17: 102400, 18: 153600,
            19: 204800, 20: 307200,
        }
        return xp_by_cr.get(self.challenge_rating, 0)

    def get_str_mod(self) -> int:
        return (self.strength - 10) // 2

    def get_dex_mod(self) -> int:
        return (self.dexterity - 10) // 2

    def get_con_mod(self) -> int:
        return (self.constitution - 10) // 2


# =============================================================================
# BESTIARY - Common Monsters organized by CR
# =============================================================================

BESTIARY: dict[str, Monster] = {}


def _register(monster: Monster) -> Monster:
    """Register a monster in the bestiary."""
    BESTIARY[monster.name.lower()] = monster
    return monster


# -----------------------------------------------------------------------------
# CR 1/4 Monsters
# -----------------------------------------------------------------------------

_register(Monster(
    name="Goblin",
    monster_type=MonsterType.HUMANOID,
    subtypes=["goblinoid"],
    size=Size.SMALL,
    challenge_rating=0.33,
    hit_dice="1d10",
    hp=6,
    armor_class=16,
    touch_ac=13,
    flat_footed_ac=14,
    speed=30,
    strength=11,
    dexterity=15,
    constitution=12,
    intelligence=10,
    wisdom=9,
    charisma=6,
    fortitude=3,
    reflex=4,
    will=-1,
    base_attack_bonus=1,
    cmb=0,
    cmd=12,
    initiative=6,
    attacks=[
        Attack("Short Sword", 2, "1d4", 0, "piercing"),
        Attack("Short Bow", 4, "1d4", 0, "piercing"),
    ],
    darkvision=60,
    skills={"Stealth": 10, "Ride": 6, "Perception": -1},
    feats=["Improved Initiative"],
    description="Goblins are short, ugly humanoids with a penchant for fire and sadistic behavior.",
    environment="Temperate forest or plains",
    organization="Gang (4-9), warband (10-16 plus goblin leader), or tribe (17+ plus leader and chief)",
    treasure="NPC gear (leather armor, light wooden shield, short sword, short bow with 20 arrows)",
    alignment="NE",
))

_register(Monster(
    name="Skeleton",
    monster_type=MonsterType.UNDEAD,
    size=Size.MEDIUM,
    challenge_rating=0.33,
    hit_dice="1d8",
    hp=4,
    armor_class=16,
    touch_ac=12,
    flat_footed_ac=14,
    speed=30,
    strength=15,
    dexterity=14,
    constitution=0,
    intelligence=0,
    wisdom=10,
    charisma=10,
    fortitude=0,
    reflex=2,
    will=2,
    base_attack_bonus=0,
    cmb=2,
    cmd=14,
    initiative=6,
    attacks=[
        Attack("Broken Scimitar", 2, "1d6", 2, "slashing"),
        Attack("Claw", 2, "1d4", 2, "slashing"),
    ],
    damage_reduction="5/bludgeoning",
    immunities=["cold", "undead traits"],
    darkvision=60,
    feats=["Improved Initiative"],
    description="Animated bones of the dead, skeletons are mindless undead that attack the living.",
    environment="Any",
    organization="Any",
    treasure="None (broken equipment)",
    alignment="NE",
))

_register(Monster(
    name="Zombie",
    monster_type=MonsterType.UNDEAD,
    size=Size.MEDIUM,
    challenge_rating=0.5,
    hit_dice="2d8+3",
    hp=12,
    armor_class=12,
    touch_ac=10,
    flat_footed_ac=12,
    speed=30,
    strength=17,
    dexterity=10,
    constitution=0,
    intelligence=0,
    wisdom=10,
    charisma=10,
    fortitude=0,
    reflex=0,
    will=3,
    base_attack_bonus=1,
    cmb=4,
    cmd=14,
    initiative=0,
    attacks=[
        Attack("Slam", 4, "1d6", 4, "bludgeoning"),
    ],
    damage_reduction="5/slashing",
    immunities=["undead traits"],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Staggered", "Zombies can only take a single move or standard action each round.", "Ex"),
    ],
    feats=["Toughness"],
    description="Shambling corpses animated by dark magic, zombies hunger for the flesh of the living.",
    environment="Any",
    organization="Any",
    treasure="None",
    alignment="NE",
))

# -----------------------------------------------------------------------------
# CR 1/2 Monsters
# -----------------------------------------------------------------------------

_register(Monster(
    name="Orc",
    monster_type=MonsterType.HUMANOID,
    subtypes=["orc"],
    size=Size.MEDIUM,
    challenge_rating=0.33,
    hit_dice="1d10+1",
    hp=6,
    armor_class=13,
    touch_ac=10,
    flat_footed_ac=13,
    speed=30,
    strength=17,
    dexterity=11,
    constitution=12,
    intelligence=7,
    wisdom=8,
    charisma=6,
    fortitude=3,
    reflex=0,
    will=-1,
    base_attack_bonus=1,
    cmb=4,
    cmd=14,
    initiative=0,
    attacks=[
        Attack("Falchion", 5, "2d4", 4, "slashing"),
        Attack("Javelin", 1, "1d6", 3, "piercing"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Ferocity", "An orc can fight for 1 more round after being reduced to 0 or fewer HP.", "Ex"),
        SpecialAbility("Light Sensitivity", "Orcs are dazzled in bright sunlight.", "Ex"),
    ],
    skills={"Intimidate": 2},
    feats=["Weapon Focus (falchion)"],
    description="Orcs are aggressive humanoids that worship strength and power above all else.",
    environment="Temperate hills, mountains, or underground",
    organization="Gang (2-4), squad (11-20 plus 2 sergeants and 1 leader), or band (30-100)",
    treasure="Standard (studded leather, falchion, 4 javelins)",
    alignment="CE",
))

_register(Monster(
    name="Giant Rat",
    monster_type=MonsterType.ANIMAL,
    size=Size.SMALL,
    challenge_rating=0.25,
    hit_dice="1d8",
    hp=4,
    armor_class=14,
    touch_ac=14,
    flat_footed_ac=11,
    speed=40,
    strength=6,
    dexterity=17,
    constitution=10,
    intelligence=2,
    wisdom=13,
    charisma=4,
    fortitude=2,
    reflex=5,
    will=1,
    base_attack_bonus=0,
    cmb=-3,
    cmd=10,
    initiative=3,
    attacks=[
        Attack("Bite", 3, "1d4", -2, "piercing", "plus disease"),
    ],
    low_light_vision=True,
    scent=True,
    special_abilities=[
        SpecialAbility("Disease", "Filth Fever: Bite—injury; save Fort DC 10; onset 1d3 days; frequency 1/day; effect 1d3 Dex damage and 1d3 Con damage; cure 2 consecutive saves.", "Ex"),
    ],
    skills={"Climb": 11, "Perception": 4, "Stealth": 11, "Swim": 11},
    description="Giant rats are dog-sized rodents that spread disease and infest sewers and ruins.",
    environment="Any urban or underground",
    organization="Pack (2-20) or swarm (21-50)",
    treasure="None",
    alignment="N",
))

_register(Monster(
    name="Giant Spider",
    monster_type=MonsterType.VERMIN,
    size=Size.MEDIUM,
    challenge_rating=1,
    hit_dice="2d8+2",
    hp=11,
    armor_class=14,
    touch_ac=12,
    flat_footed_ac=12,
    speed=30,
    strength=11,
    dexterity=15,
    constitution=12,
    intelligence=0,
    wisdom=10,
    charisma=2,
    fortitude=4,
    reflex=2,
    will=0,
    base_attack_bonus=1,
    cmb=1,
    cmd=13,
    initiative=2,
    attacks=[
        Attack("Bite", 2, "1d6", 0, "piercing", "plus poison"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Poison", "Bite—injury; save Fort DC 14; frequency 1/round for 4 rounds; effect 1d2 Strength damage; cure 1 save.", "Ex"),
        SpecialAbility("Web", "Can throw webs up to 8 times per day. Entangle attack, DC 12 to escape.", "Ex"),
    ],
    skills={"Climb": 16, "Perception": 4},
    immunities=["mind-affecting effects"],
    description="Giant spiders lurk in dark places, spinning webs to trap unwary prey.",
    environment="Any",
    organization="Solitary, pair, or colony (3-8)",
    treasure="Incidental",
    alignment="N",
))

# -----------------------------------------------------------------------------
# CR 1 Monsters
# -----------------------------------------------------------------------------

_register(Monster(
    name="Hobgoblin",
    monster_type=MonsterType.HUMANOID,
    subtypes=["goblinoid"],
    size=Size.MEDIUM,
    challenge_rating=0.5,
    hit_dice="1d10+2",
    hp=7,
    armor_class=16,
    touch_ac=11,
    flat_footed_ac=15,
    speed=30,
    strength=15,
    dexterity=13,
    constitution=14,
    intelligence=10,
    wisdom=12,
    charisma=8,
    fortitude=4,
    reflex=1,
    will=1,
    base_attack_bonus=1,
    cmb=3,
    cmd=14,
    initiative=1,
    attacks=[
        Attack("Longsword", 3, "1d8", 2, "slashing"),
        Attack("Longbow", 2, "1d8", 0, "piercing"),
    ],
    darkvision=60,
    skills={"Perception": 2, "Stealth": 4},
    feats=["Toughness"],
    description="Hobgoblins are militaristic and disciplined goblinoids that organize into armies.",
    environment="Temperate hills",
    organization="Gang (4-9), warband (10-24), or tribe (25-200)",
    treasure="NPC gear (scale mail, heavy steel shield, longsword, longbow with 20 arrows)",
    alignment="LE",
))

_register(Monster(
    name="Wolf",
    monster_type=MonsterType.ANIMAL,
    size=Size.MEDIUM,
    challenge_rating=1,
    hit_dice="2d8+4",
    hp=13,
    armor_class=14,
    touch_ac=12,
    flat_footed_ac=12,
    speed=50,
    strength=13,
    dexterity=15,
    constitution=15,
    intelligence=2,
    wisdom=12,
    charisma=6,
    fortitude=5,
    reflex=5,
    will=1,
    base_attack_bonus=1,
    cmb=2,
    cmd=14,
    initiative=2,
    attacks=[
        Attack("Bite", 3, "1d6", 1, "piercing", "plus trip"),
    ],
    low_light_vision=True,
    scent=True,
    special_abilities=[
        SpecialAbility("Trip", "A wolf that hits with a bite attack can attempt to trip the opponent as a free action.", "Ex"),
    ],
    skills={"Perception": 8, "Stealth": 6, "Survival": 1},
    description="Wolves are pack hunters that use coordinated tactics to bring down prey.",
    environment="Cold or temperate forests",
    organization="Solitary, pair, or pack (3-12)",
    treasure="None",
    alignment="N",
))

_register(Monster(
    name="Ghoul",
    monster_type=MonsterType.UNDEAD,
    size=Size.MEDIUM,
    challenge_rating=1,
    hit_dice="2d8",
    hp=9,
    armor_class=14,
    touch_ac=12,
    flat_footed_ac=12,
    speed=30,
    strength=13,
    dexterity=15,
    constitution=0,
    intelligence=13,
    wisdom=14,
    charisma=14,
    fortitude=0,
    reflex=2,
    will=5,
    base_attack_bonus=1,
    cmb=2,
    cmd=14,
    initiative=2,
    attacks=[
        Attack("Bite", 3, "1d6", 1, "piercing", "plus disease and paralysis"),
        Attack("Claw", 3, "1d6", 1, "slashing", "plus paralysis"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Disease", "Ghoul Fever: Bite—injury; save Fort DC 13; onset 1 day; frequency 1/day; effect 1d3 Con and 1d3 Dex damage; cure 2 consecutive saves.", "Su"),
        SpecialAbility("Paralysis", "Those hit by a ghoul's bite or claw attack must succeed on a DC 13 Fortitude save or be paralyzed for 1d4+1 rounds. Elves are immune.", "Su"),
    ],
    immunities=["undead traits"],
    skills={"Acrobatics": 4, "Climb": 5, "Perception": 7, "Stealth": 7, "Swim": 3},
    description="Ghouls are undead creatures that hunger for the flesh of the living.",
    environment="Any land",
    organization="Solitary, gang (2-4), or pack (7-12)",
    treasure="Standard",
    alignment="CE",
))

# -----------------------------------------------------------------------------
# CR 2 Monsters
# -----------------------------------------------------------------------------

_register(Monster(
    name="Bugbear",
    monster_type=MonsterType.HUMANOID,
    subtypes=["goblinoid"],
    size=Size.MEDIUM,
    challenge_rating=2,
    hit_dice="3d8+6",
    hp=19,
    armor_class=17,
    touch_ac=12,
    flat_footed_ac=15,
    speed=30,
    strength=16,
    dexterity=14,
    constitution=15,
    intelligence=10,
    wisdom=12,
    charisma=9,
    fortitude=3,
    reflex=5,
    will=1,
    base_attack_bonus=2,
    cmb=5,
    cmd=17,
    initiative=2,
    attacks=[
        Attack("Morningstar", 5, "1d8", 3, "bludgeoning/piercing"),
        Attack("Javelin", 4, "1d6", 3, "piercing"),
    ],
    darkvision=60,
    scent=True,
    special_abilities=[
        SpecialAbility("Stalker", "+4 racial bonus on Intimidate and Stealth checks.", "Ex"),
    ],
    skills={"Intimidate": 6, "Perception": 6, "Stealth": 9},
    feats=["Skill Focus (Perception)"],
    description="Bugbears are massive, hairy goblinoids that delight in ambushes and cruel violence.",
    environment="Temperate mountains",
    organization="Solitary, pair, gang (3-6), or troupe (7-12)",
    treasure="NPC gear (leather armor, heavy wooden shield, morningstar, 3 javelins)",
    alignment="CE",
))

_register(Monster(
    name="Dire Wolf",
    monster_type=MonsterType.ANIMAL,
    size=Size.LARGE,
    challenge_rating=3,
    hit_dice="6d8+18",
    hp=45,
    armor_class=14,
    touch_ac=11,
    flat_footed_ac=12,
    speed=50,
    strength=25,
    dexterity=15,
    constitution=17,
    intelligence=2,
    wisdom=12,
    charisma=10,
    fortitude=8,
    reflex=7,
    will=6,
    base_attack_bonus=4,
    cmb=12,
    cmd=24,
    initiative=2,
    attacks=[
        Attack("Bite", 10, "1d8", 10, "piercing", "plus trip"),
    ],
    low_light_vision=True,
    scent=True,
    special_abilities=[
        SpecialAbility("Trip", "A dire wolf that hits with a bite attack can attempt to trip as a free action.", "Ex"),
    ],
    skills={"Perception": 10, "Stealth": 4, "Survival": 3},
    description="Dire wolves are immense wolves that can serve as mounts for Medium creatures.",
    environment="Cold or temperate forests",
    organization="Solitary, pair, or pack (3-8)",
    treasure="None",
    alignment="N",
))

_register(Monster(
    name="Ogre",
    monster_type=MonsterType.HUMANOID,
    subtypes=["giant"],
    size=Size.LARGE,
    challenge_rating=3,
    hit_dice="4d8+16",
    hp=34,
    armor_class=17,
    touch_ac=8,
    flat_footed_ac=17,
    speed=30,
    strength=21,
    dexterity=8,
    constitution=18,
    intelligence=6,
    wisdom=10,
    charisma=7,
    fortitude=8,
    reflex=0,
    will=1,
    base_attack_bonus=3,
    cmb=9,
    cmd=18,
    initiative=-1,
    attacks=[
        Attack("Greatclub", 8, "2d8", 7, "bludgeoning"),
        Attack("Javelin", 1, "1d8", 5, "piercing"),
    ],
    darkvision=60,
    low_light_vision=True,
    skills={"Climb": 7, "Perception": 5},
    description="Ogres are brutish giants that prey on humanoids and livestock.",
    environment="Temperate or cold hills",
    organization="Solitary, pair, gang (3-4), or family (5-16)",
    treasure="Standard (hide armor, greatclub, 4 javelins)",
    alignment="CE",
))

_register(Monster(
    name="Wight",
    monster_type=MonsterType.UNDEAD,
    size=Size.MEDIUM,
    challenge_rating=3,
    hit_dice="4d8+8",
    hp=26,
    armor_class=15,
    touch_ac=11,
    flat_footed_ac=14,
    speed=30,
    strength=12,
    dexterity=12,
    constitution=0,
    intelligence=11,
    wisdom=13,
    charisma=15,
    fortitude=3,
    reflex=2,
    will=5,
    base_attack_bonus=3,
    cmb=4,
    cmd=15,
    initiative=1,
    attacks=[
        Attack("Slam", 4, "1d4", 1, "bludgeoning", "plus energy drain"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Create Spawn", "Any humanoid slain by a wight becomes a wight in 1d4 rounds.", "Su"),
        SpecialAbility("Energy Drain", "Living creatures hit by a wight's slam attack gain one negative level. DC 14 Fortitude to remove after 24 hours.", "Su"),
    ],
    immunities=["undead traits"],
    skills={"Intimidate": 9, "Knowledge (religion)": 4, "Perception": 11, "Stealth": 16},
    feats=["Blind-Fight", "Skill Focus (Perception)"],
    description="Wights are undead creatures that drain the life force of the living.",
    environment="Any",
    organization="Solitary, pair, gang (3-6), or pack (7-12)",
    treasure="Standard",
    alignment="LE",
))

# -----------------------------------------------------------------------------
# CR 4-5 Monsters
# -----------------------------------------------------------------------------

_register(Monster(
    name="Owlbear",
    monster_type=MonsterType.MAGICAL_BEAST,
    size=Size.LARGE,
    challenge_rating=4,
    hit_dice="5d10+25",
    hp=52,
    armor_class=15,
    touch_ac=10,
    flat_footed_ac=14,
    speed=30,
    strength=19,
    dexterity=12,
    constitution=18,
    intelligence=2,
    wisdom=12,
    charisma=10,
    fortitude=8,
    reflex=5,
    will=2,
    base_attack_bonus=5,
    cmb=10,
    cmd=21,
    initiative=1,
    attacks=[
        Attack("Claw", 8, "1d6", 4, "slashing", "plus grab"),
        Attack("Bite", 8, "1d6", 4, "piercing"),
    ],
    darkvision=60,
    low_light_vision=True,
    scent=True,
    special_abilities=[
        SpecialAbility("Grab", "If an owlbear hits with a claw, it can attempt to start a grapple as a free action.", "Ex"),
    ],
    skills={"Perception": 12},
    description="Owlbears are fierce, territorial creatures with the body of a bear and the head of an owl.",
    environment="Temperate forests",
    organization="Solitary, pair, or pack (3-8)",
    treasure="Incidental",
    alignment="N",
))

_register(Monster(
    name="Minotaur",
    monster_type=MonsterType.MONSTROUS_HUMANOID,
    size=Size.LARGE,
    challenge_rating=4,
    hit_dice="6d10+18",
    hp=51,
    armor_class=14,
    touch_ac=11,
    flat_footed_ac=12,
    speed=30,
    strength=19,
    dexterity=10,
    constitution=15,
    intelligence=7,
    wisdom=10,
    charisma=8,
    fortitude=7,
    reflex=5,
    will=5,
    base_attack_bonus=6,
    cmb=11,
    cmd=21,
    initiative=0,
    attacks=[
        Attack("Greataxe", 10, "3d6", 6, "slashing"),
        Attack("Gore", 5, "1d6", 2, "piercing"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Natural Cunning", "Immune to maze spells. Never gets lost. Can track opponents by scent.", "Ex"),
        SpecialAbility("Powerful Charge", "Gore attack deals 2d6+6 damage on a charge.", "Ex"),
    ],
    skills={"Intimidate": 5, "Perception": 10, "Stealth": 2, "Survival": 10},
    feats=["Great Fortitude", "Power Attack", "Improved Bull Rush"],
    description="Minotaurs are savage bull-headed humanoids that dwell in labyrinths.",
    environment="Temperate ruins or underground",
    organization="Solitary, pair, or gang (3-4)",
    treasure="Standard (hide armor, greataxe)",
    alignment="CE",
))

_register(Monster(
    name="Troll",
    monster_type=MonsterType.HUMANOID,
    subtypes=["giant"],
    size=Size.LARGE,
    challenge_rating=5,
    hit_dice="6d8+36",
    hp=63,
    armor_class=16,
    touch_ac=14,
    flat_footed_ac=13,
    speed=30,
    strength=21,
    dexterity=14,
    constitution=23,
    intelligence=6,
    wisdom=9,
    charisma=6,
    fortitude=11,
    reflex=6,
    will=3,
    base_attack_bonus=4,
    cmb=10,
    cmd=22,
    initiative=2,
    attacks=[
        Attack("Bite", 8, "1d8", 5, "piercing"),
        Attack("Claw", 8, "1d6", 5, "slashing", "plus rend"),
    ],
    darkvision=60,
    low_light_vision=True,
    scent=True,
    special_abilities=[
        SpecialAbility("Regeneration 5", "Fire and acid deal normal damage to a troll. If a troll loses a limb, the limb regrows in 3d6 minutes.", "Ex"),
        SpecialAbility("Rend", "If a troll hits with both claw attacks, it latches onto the opponent's body and tears the flesh, dealing an extra 1d6+7 damage.", "Ex"),
    ],
    skills={"Perception": 8},
    description="Trolls are fearsome giants known for their incredible regenerative abilities.",
    environment="Cold mountains",
    organization="Solitary or gang (2-4)",
    treasure="Standard",
    alignment="CE",
))

_register(Monster(
    name="Wraith",
    monster_type=MonsterType.UNDEAD,
    subtypes=["incorporeal"],
    size=Size.MEDIUM,
    challenge_rating=5,
    hit_dice="5d8+15",
    hp=37,
    armor_class=18,
    touch_ac=18,
    flat_footed_ac=14,
    speed=0,  # Fly 60 ft
    strength=0,
    dexterity=18,
    constitution=0,
    intelligence=14,
    wisdom=14,
    charisma=17,
    fortitude=4,
    reflex=5,
    will=6,
    base_attack_bonus=3,
    cmb=3,
    cmd=17,
    initiative=8,
    attacks=[
        Attack("Incorporeal Touch", 7, "1d6", 0, "negative energy", "plus 1d6 Con drain"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Constitution Drain", "Living creatures hit by a wraith's touch must succeed on a DC 15 Fortitude save or take 1d6 Constitution drain.", "Su"),
        SpecialAbility("Create Spawn", "Any humanoid slain by a wraith becomes a wraith in 1d4 rounds.", "Su"),
        SpecialAbility("Incorporeal", "Can only be harmed by other incorporeal creatures, magic weapons, or spells.", "Su"),
        SpecialAbility("Sunlight Powerlessness", "A wraith caught in sunlight cannot attack and is staggered.", "Ex"),
    ],
    immunities=["undead traits"],
    skills={"Diplomacy": 8, "Fly": 14, "Intimidate": 11, "Knowledge (planes)": 7, "Perception": 10, "Sense Motive": 10, "Stealth": 12},
    feats=["Blind-Fight", "Combat Reflexes", "Improved Initiative"],
    description="Wraiths are malevolent incorporeal undead that drain the life essence from the living.",
    environment="Any",
    organization="Solitary, pair, gang (3-6), or pack (7-12)",
    treasure="None",
    alignment="LE",
))

# -----------------------------------------------------------------------------
# CR 6+ Monsters
# -----------------------------------------------------------------------------

_register(Monster(
    name="Hill Giant",
    monster_type=MonsterType.HUMANOID,
    subtypes=["giant"],
    size=Size.LARGE,
    challenge_rating=7,
    hit_dice="10d8+50",
    hp=95,
    armor_class=21,
    touch_ac=9,
    flat_footed_ac=21,
    speed=40,
    strength=25,
    dexterity=8,
    constitution=19,
    intelligence=6,
    wisdom=10,
    charisma=7,
    fortitude=11,
    reflex=2,
    will=3,
    base_attack_bonus=7,
    cmb=15,
    cmd=24,
    initiative=-1,
    attacks=[
        Attack("Greatclub", 14, "2d8", 10, "bludgeoning"),
        Attack("Rock Throw", 5, "1d8", 7, "bludgeoning"),
    ],
    darkvision=60,
    low_light_vision=True,
    special_abilities=[
        SpecialAbility("Rock Catching", "Can catch Small, Medium, or Large rocks as a free action once per round.", "Ex"),
        SpecialAbility("Rock Throwing", "Range increment 120 feet.", "Ex"),
    ],
    skills={"Climb": 10, "Perception": 6},
    feats=["Cleave", "Intimidating Prowess", "Martial Weapon Proficiency (greatclub)", "Power Attack", "Weapon Focus (greatclub)"],
    description="Hill giants are the least powerful of the true giants, but still dangerous foes.",
    environment="Temperate hills",
    organization="Solitary, gang (2-5), band (6-8), or tribe (9-30)",
    treasure="Standard (hide armor, greatclub)",
    alignment="CE",
))

_register(Monster(
    name="Young Red Dragon",
    monster_type=MonsterType.DRAGON,
    subtypes=["fire"],
    size=Size.LARGE,
    challenge_rating=10,
    hit_dice="13d12+52",
    hp=136,
    armor_class=24,
    touch_ac=10,
    flat_footed_ac=23,
    speed=40,
    strength=25,
    dexterity=12,
    constitution=19,
    intelligence=12,
    wisdom=13,
    charisma=12,
    fortitude=12,
    reflex=9,
    will=9,
    base_attack_bonus=13,
    cmb=21,
    cmd=32,
    initiative=5,
    attacks=[
        Attack("Bite", 20, "2d6", 10, "piercing/slashing"),
        Attack("Claw", 20, "1d8", 7, "slashing"),
        Attack("Wing", 15, "1d6", 3, "bludgeoning"),
        Attack("Tail Slap", 15, "1d8", 10, "bludgeoning"),
    ],
    darkvision=120,
    low_light_vision=True,
    blindsense=60,
    special_abilities=[
        SpecialAbility("Breath Weapon", "40 ft. cone, 6d10 fire damage, Reflex DC 20 for half, usable every 1d4 rounds.", "Su"),
        SpecialAbility("Fire Subtype", "Immunity to fire, vulnerability to cold.", "Ex"),
        SpecialAbility("Frightful Presence", "180 ft., DC 17 Will save or shaken for 5d6 rounds.", "Su"),
    ],
    immunities=["fire", "paralysis", "sleep"],
    spell_resistance=21,
    skills={"Appraise": 11, "Bluff": 11, "Fly": 9, "Intimidate": 11, "Perception": 17, "Sense Motive": 11, "Stealth": 9},
    feats=["Cleave", "Improved Initiative", "Improved Vital Strike", "Power Attack", "Vital Strike"],
    description="Red dragons are the most covetous and greedy of dragonkind, obsessed with wealth and domination.",
    environment="Warm mountains",
    organization="Solitary",
    treasure="Triple",
    alignment="CE",
))

_register(Monster(
    name="Vampire",
    monster_type=MonsterType.UNDEAD,
    subtypes=["augmented humanoid"],
    size=Size.MEDIUM,
    challenge_rating=9,
    hit_dice="10d8+30",
    hp=75,
    armor_class=23,
    touch_ac=17,
    flat_footed_ac=17,
    speed=30,
    strength=22,
    dexterity=24,
    constitution=0,
    intelligence=16,
    wisdom=16,
    charisma=20,
    fortitude=8,
    reflex=14,
    will=10,
    base_attack_bonus=7,
    cmb=13,
    cmd=30,
    initiative=11,
    attacks=[
        Attack("Slam", 13, "1d6", 6, "bludgeoning", "plus energy drain"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Blood Drain", "A vampire can drain blood from a grappled opponent, dealing 1d4 Constitution damage each round.", "Su"),
        SpecialAbility("Children of the Night", "Once per day, summon 1d6+1 rat swarms, 1d4+1 bat swarms, or 3d6 wolves.", "Su"),
        SpecialAbility("Create Spawn", "A humanoid slain by a vampire's energy drain rises as a vampire spawn 1d4 days later.", "Su"),
        SpecialAbility("Dominate", "As dominate person, DC 20 Will save, caster level 12th.", "Su"),
        SpecialAbility("Energy Drain", "Slam attack bestows two negative levels. DC 20 Fortitude to remove after 24 hours.", "Su"),
        SpecialAbility("Gaseous Form", "At will, as the spell.", "Su"),
        SpecialAbility("Spider Climb", "As the spell, always active.", "Ex"),
    ],
    damage_reduction="10/magic and silver",
    immunities=["undead traits"],
    resistances={"cold": 10, "electricity": 10},
    feats=["Alertness", "Combat Reflexes", "Dodge", "Improved Initiative", "Lightning Reflexes", "Toughness"],
    description="Vampires are undead lords of the night who sustain themselves on the blood of the living.",
    environment="Any",
    organization="Solitary, pair, gang (3-4), or coven (5-8)",
    treasure="Double",
    alignment="CE",
))

_register(Monster(
    name="Lich",
    monster_type=MonsterType.UNDEAD,
    subtypes=["augmented humanoid"],
    size=Size.MEDIUM,
    challenge_rating=12,
    hit_dice="11d6+44",
    hp=82,
    armor_class=23,
    touch_ac=14,
    flat_footed_ac=20,
    speed=30,
    strength=10,
    dexterity=16,
    constitution=0,
    intelligence=24,
    wisdom=14,
    charisma=16,
    fortitude=6,
    reflex=8,
    will=13,
    base_attack_bonus=5,
    cmb=5,
    cmd=18,
    initiative=7,
    attacks=[
        Attack("Touch", 8, "1d8+5", 0, "negative energy", "plus paralysis"),
    ],
    darkvision=60,
    special_abilities=[
        SpecialAbility("Fear Aura", "60 ft., DC 18 Will save or affected as by fear for 2d4 rounds.", "Su"),
        SpecialAbility("Paralyzing Touch", "Permanent paralysis, DC 18 Fortitude negates. Remove with remove paralysis or any spell that removes curse.", "Su"),
        SpecialAbility("Spells", "Casts as 11th level wizard.", "Su"),
        SpecialAbility("Rejuvenation", "When destroyed, the lich reforms near its phylactery in 1d10 days.", "Su"),
    ],
    damage_reduction="15/bludgeoning and magic",
    immunities=["cold", "electricity", "undead traits"],
    spell_resistance=24,
    feats=["Combat Casting", "Craft Wondrous Item", "Extend Spell", "Improved Initiative", "Iron Will", "Maximize Spell", "Quicken Spell", "Scribe Scroll", "Silent Spell"],
    description="A lich is an undead spellcaster who has used dark magic to bind their soul to a phylactery, achieving immortality.",
    environment="Any",
    organization="Solitary",
    treasure="Double standard plus phylactery",
    alignment="NE",
))


# =============================================================================
# Utility Functions
# =============================================================================

def get_monster(name: str) -> Monster | None:
    """Get a monster by name (case-insensitive)."""
    return BESTIARY.get(name.lower())


def get_monsters_by_cr(cr: float) -> list[Monster]:
    """Get all monsters of a specific CR."""
    return [m for m in BESTIARY.values() if m.challenge_rating == cr]


def get_monsters_by_type(monster_type: MonsterType) -> list[Monster]:
    """Get all monsters of a specific type."""
    return [m for m in BESTIARY.values() if m.monster_type == monster_type]


def get_monsters_by_cr_range(min_cr: float, max_cr: float) -> list[Monster]:
    """Get all monsters within a CR range."""
    return [m for m in BESTIARY.values() if min_cr <= m.challenge_rating <= max_cr]


def list_all_monsters() -> list[Monster]:
    """Get all monsters sorted by CR then name."""
    return sorted(BESTIARY.values(), key=lambda m: (m.challenge_rating, m.name))


def get_encounter_monsters(party_level: int, party_size: int = 4) -> list[Monster]:
    """Get monsters appropriate for an average party level."""
    # APL (Average Party Level) determines base CR
    apl = party_level

    # Get monsters from APL-2 to APL+2
    min_cr = max(0.25, apl - 2)
    max_cr = apl + 2

    return get_monsters_by_cr_range(min_cr, max_cr)


def generate_encounter(
    party_level: int,
    difficulty: str = "medium",
    environment: str | None = None,
) -> list[tuple[Monster, int]]:
    """
    Generate a random encounter appropriate for the party level.

    Args:
        party_level: Average party level
        difficulty: "easy", "medium", "hard", or "deadly"
        environment: Optional environment filter (e.g., "forest", "underground")

    Returns:
        List of (Monster, count) tuples
    """
    import random

    # XP budgets based on difficulty (for 4 players)
    xp_budgets = {
        "easy": party_level * 300,
        "medium": party_level * 500,
        "hard": party_level * 800,
        "deadly": party_level * 1200,
    }
    budget = xp_budgets.get(difficulty, xp_budgets["medium"])

    # Get appropriate monsters
    candidates = get_encounter_monsters(party_level)

    # Filter by environment if specified
    if environment:
        env_lower = environment.lower()
        candidates = [m for m in candidates if env_lower in m.environment.lower()]

    if not candidates:
        candidates = get_encounter_monsters(party_level)

    # Build encounter
    encounter: list[tuple[Monster, int]] = []
    remaining_budget = budget

    # Try to build a varied encounter
    attempts = 0
    while remaining_budget > 50 and attempts < 20:
        attempts += 1

        # Pick a random monster that fits the budget
        affordable = [m for m in candidates if m.get_xp_reward() <= remaining_budget]
        if not affordable:
            break

        monster = random.choice(affordable)
        xp_cost = monster.get_xp_reward()

        # Determine how many to add (favor smaller groups for variety)
        max_count = min(4, remaining_budget // xp_cost)
        if max_count < 1:
            continue

        # Weight toward smaller numbers
        weights = [3, 2, 1, 1][:max_count]
        count = random.choices(range(1, max_count + 1), weights=weights)[0]

        # Check if we already have this monster
        existing = next((e for e in encounter if e[0].name == monster.name), None)
        if existing:
            # Add to existing count
            idx = encounter.index(existing)
            encounter[idx] = (monster, existing[1] + count)
        else:
            encounter.append((monster, count))

        remaining_budget -= xp_cost * count

    return encounter


def create_combatant_from_monster(monster: Monster, name_suffix: str = "") -> "Combatant":
    """
    Create a Combatant from a Monster for use in combat.

    Args:
        monster: The monster to create a combatant from
        name_suffix: Optional suffix for the name (e.g., " 1", " 2")

    Returns:
        A Combatant instance
    """
    from .combat import Combatant, CombatantType

    # Get primary attack
    primary_attack = monster.attacks[0] if monster.attacks else None

    return Combatant(
        name=monster.name + name_suffix,
        combatant_type=CombatantType.ENEMY,
        max_hp=monster.hp,
        current_hp=monster.hp,
        armor_class=monster.armor_class,
        touch_ac=monster.touch_ac,
        flat_footed_ac=monster.flat_footed_ac,
        attack_bonus=primary_attack.attack_bonus if primary_attack else monster.base_attack_bonus,
        damage_dice=primary_attack.damage_dice if primary_attack else "1d4",
        damage_bonus=primary_attack.damage_bonus if primary_attack else 0,
        initiative_modifier=monster.initiative,
    )
