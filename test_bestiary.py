"""Test script for the bestiary system."""

from src.game.bestiary import (
    BESTIARY,
    MonsterType,
    Size,
    get_monster,
    get_monsters_by_cr,
    get_monsters_by_type,
    get_monsters_by_cr_range,
    list_all_monsters,
    get_encounter_monsters,
    generate_encounter,
    create_combatant_from_monster,
)
from src.game.combat import CombatTracker, CombatantType


def test_bestiary():
    print("=" * 60)
    print("   BESTIARY TEST")
    print("=" * 60)
    print()

    # List all monsters
    all_monsters = list_all_monsters()
    print(f"Total monsters in bestiary: {len(all_monsters)}")
    print()

    # Show monsters by CR
    print("Monsters by CR:")
    cr_counts = {}
    for monster in all_monsters:
        cr = monster.challenge_rating
        cr_counts[cr] = cr_counts.get(cr, 0) + 1
    for cr in sorted(cr_counts.keys()):
        cr_str = f"CR {cr}" if cr >= 1 else f"CR 1/{int(1/cr)}"
        print(f"  {cr_str}: {cr_counts[cr]} monsters")
    print()

    # Show monsters by type
    print("Monsters by Type:")
    for monster_type in MonsterType:
        monsters = get_monsters_by_type(monster_type)
        if monsters:
            print(f"  {monster_type.value}: {len(monsters)}")
    print()

    # Test getting specific monsters
    print("-" * 60)
    print("Sample Monster: Goblin")
    print("-" * 60)
    goblin = get_monster("goblin")
    if goblin:
        print(f"  Name: {goblin.name}")
        print(f"  Type: {goblin.monster_type.value} ({', '.join(goblin.subtypes)})")
        print(f"  Size: {goblin.size.value}")
        print(f"  CR: {goblin.challenge_rating} ({goblin.get_xp_reward()} XP)")
        print(f"  HP: {goblin.hp} ({goblin.hit_dice})")
        print(f"  AC: {goblin.armor_class} (touch {goblin.touch_ac}, flat-footed {goblin.flat_footed_ac})")
        print(f"  Attacks:")
        for attack in goblin.attacks:
            print(f"    - {attack.name}: +{attack.attack_bonus} ({attack.damage_dice}+{attack.damage_bonus})")
        print(f"  Darkvision: {goblin.darkvision} ft.")
        print(f"  Environment: {goblin.environment}")
    print()

    # Test getting a high CR monster
    print("-" * 60)
    print("Sample Monster: Young Red Dragon")
    print("-" * 60)
    dragon = get_monster("young red dragon")
    if dragon:
        print(f"  Name: {dragon.name}")
        print(f"  Type: {dragon.monster_type.value}")
        print(f"  Size: {dragon.size.value}")
        print(f"  CR: {dragon.challenge_rating} ({dragon.get_xp_reward():,} XP)")
        print(f"  HP: {dragon.hp} ({dragon.hit_dice})")
        print(f"  AC: {dragon.armor_class}")
        print(f"  Attacks:")
        for attack in dragon.attacks:
            special = f" ({attack.special})" if attack.special else ""
            print(f"    - {attack.name}: +{attack.attack_bonus} ({attack.damage_dice}+{attack.damage_bonus}){special}")
        print(f"  Special Abilities:")
        for ability in dragon.special_abilities:
            print(f"    - {ability.name} ({ability.ability_type})")
        print(f"  Immunities: {', '.join(dragon.immunities)}")
        print(f"  SR: {dragon.spell_resistance}")
    print()

    # Test encounter generation
    print("-" * 60)
    print("Encounter Generation Test (Party Level 3)")
    print("-" * 60)
    for difficulty in ["easy", "medium", "hard", "deadly"]:
        encounter = generate_encounter(party_level=3, difficulty=difficulty)
        total_xp = sum(m.get_xp_reward() * count for m, count in encounter)
        print(f"\n{difficulty.upper()} Encounter ({total_xp} XP):")
        for monster, count in encounter:
            cr_str = f"CR {monster.challenge_rating}" if monster.challenge_rating >= 1 else f"CR 1/{int(1/monster.challenge_rating)}"
            print(f"  {count}x {monster.name} ({cr_str}, {monster.get_xp_reward()} XP each)")
    print()

    # Test creating combatants from monsters
    print("-" * 60)
    print("Combat Integration Test")
    print("-" * 60)
    tracker = CombatTracker()

    # Create some combatants from monsters
    orc = get_monster("orc")
    if orc:
        for i in range(3):
            combatant = create_combatant_from_monster(orc, f" {i+1}")
            tracker.add_combatant(combatant)
            print(f"Added: {combatant.name} (HP: {combatant.max_hp}, AC: {combatant.armor_class})")

    troll = get_monster("troll")
    if troll:
        combatant = create_combatant_from_monster(troll)
        tracker.add_combatant(combatant)
        print(f"Added: {combatant.name} (HP: {combatant.max_hp}, AC: {combatant.armor_class})")

    print()
    print(f"Total combatants in tracker: {len(tracker.combatants)}")
    for c in tracker.combatants:
        print(f"  - {c.name}: HP {c.current_hp}/{c.max_hp}, AC {c.armor_class}, Attack +{c.attack_bonus}")
    print()

    # Start combat and show initiative
    tracker.start_combat()
    print("Initiative Order:")
    for i, c in enumerate(tracker.initiative_order, 1):
        print(f"  {i}. {c.name} (Init: {c.initiative})")

    print()
    print("=" * 60)
    print("   BESTIARY TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_bestiary()
