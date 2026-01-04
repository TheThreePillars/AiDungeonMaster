"""Combat test script for AI Dungeon Master."""

from src.database.session import session_scope
from src.database.models import Character
from src.game.combat import CombatTracker, Combatant, CombatantType
from src.game.dice import DiceRoller


def run_combat_test():
    print("=" * 60)
    print("   COMBAT TEST: The Adventurers vs Goblin Raiding Party")
    print("=" * 60)
    print()

    # Load party from database
    with session_scope() as session:
        party = list(session.query(Character).all())

    tracker = CombatTracker()
    roller = DiceRoller()

    # Add party members
    for char in party:
        dex_mod = (char.dexterity - 10) // 2
        str_mod = (char.strength - 10) // 2

        # Determine damage based on class
        if char.character_class == "Fighter":
            damage_dice = "1d8"
            damage_bonus = str_mod + 1  # +1 weapon
            attack_bonus = char.base_attack_bonus + str_mod + 1
        elif char.character_class == "Wizard":
            damage_dice = "1d6"
            damage_bonus = str_mod
            attack_bonus = char.base_attack_bonus + str_mod
        else:  # Cleric
            damage_dice = "1d8"
            damage_bonus = str_mod
            attack_bonus = char.base_attack_bonus + str_mod

        combatant = Combatant(
            name=char.name,
            combatant_type=CombatantType.PLAYER,
            max_hp=char.max_hp,
            current_hp=char.current_hp,
            armor_class=char.armor_class,
            touch_ac=char.touch_ac,
            flat_footed_ac=char.flat_footed_ac,
            attack_bonus=attack_bonus,
            damage_dice=damage_dice,
            damage_bonus=damage_bonus,
            initiative_modifier=dex_mod,
            character_id=char.id,
        )
        tracker.add_combatant(combatant)
        print(f"[PARTY] {char.name} - {char.race} {char.character_class} {char.level}")
        print(f"        HP: {char.current_hp}/{char.max_hp}  AC: {char.armor_class}  Attack: +{attack_bonus}")

    print()

    # Add enemies
    enemies = [
        {"name": "Goblin Warrior 1", "hp": 6, "ac": 16, "attack": 2, "damage_dice": "1d4", "damage_bonus": 0, "init": 6},
        {"name": "Goblin Warrior 2", "hp": 6, "ac": 16, "attack": 2, "damage_dice": "1d4", "damage_bonus": 0, "init": 6},
        {"name": "Goblin Warrior 3", "hp": 6, "ac": 16, "attack": 2, "damage_dice": "1d4", "damage_bonus": 0, "init": 6},
        {"name": "Goblin Archer", "hp": 5, "ac": 15, "attack": 4, "damage_dice": "1d4", "damage_bonus": 0, "init": 7},
        {"name": "Goblin Boss", "hp": 15, "ac": 17, "attack": 5, "damage_dice": "1d6", "damage_bonus": 2, "init": 5},
    ]

    for enemy in enemies:
        combatant = Combatant(
            name=enemy["name"],
            combatant_type=CombatantType.ENEMY,
            max_hp=enemy["hp"],
            current_hp=enemy["hp"],
            armor_class=enemy["ac"],
            attack_bonus=enemy["attack"],
            damage_dice=enemy["damage_dice"],
            damage_bonus=enemy["damage_bonus"],
            initiative_modifier=enemy["init"],
        )
        tracker.add_combatant(combatant)

    print("[ENEMIES] 3 Goblin Warriors, 1 Goblin Archer, 1 Goblin Boss")
    print()

    # Start combat
    tracker.start_combat()
    print(">>> ROLL INITIATIVE! <<<")
    print()

    # Show initiative order
    init_order = tracker.initiative_order
    print("Initiative Order:")
    for i, c in enumerate(init_order, 1):
        team = "PARTY" if c.combatant_type == CombatantType.PLAYER else "ENEMY"
        print(f"  {i}. [{team}] {c.name} (Init: {c.initiative})")
    print()
    print("-" * 60)

    # Run combat
    max_rounds = 10
    last_round = 0

    while tracker.round_number <= max_rounds:
        # Check if combat is over
        players_alive = [c for c in tracker.combatants if c.combatant_type == CombatantType.PLAYER and c.current_hp > 0]
        enemies_alive = [c for c in tracker.combatants if c.combatant_type == CombatantType.ENEMY and c.current_hp > 0]

        if not enemies_alive:
            print()
            print("=" * 60)
            print("   VICTORY! All enemies defeated!")
            print("=" * 60)
            break

        if not players_alive:
            print()
            print("=" * 60)
            print("   DEFEAT! The party has fallen...")
            print("=" * 60)
            break

        current = tracker.get_current_combatant()
        if not current or current.current_hp <= 0:
            tracker.next_turn()
            continue

        # Announce round start
        if tracker.round_number != last_round:
            print()
            print(f"=== ROUND {tracker.round_number} ===")
            last_round = tracker.round_number

        is_player = current.combatant_type == CombatantType.PLAYER

        # Choose target
        if is_player:
            valid_targets = enemies_alive[:]
            valid_targets.sort(key=lambda x: (x.name != "Goblin Boss", x.current_hp))
        else:
            valid_targets = players_alive[:]
            valid_targets.sort(key=lambda x: x.armor_class)

        if not valid_targets:
            tracker.next_turn()
            continue

        target = valid_targets[0]

        # Special actions for casters on round 1
        if tracker.round_number == 1 and is_player:
            if "Elara" in current.name:
                damage = roller.roll("2d4+2").total
                target.current_hp -= damage
                print(f"  {current.name} casts Magic Missile at {target.name}!")
                print(f"    -> Auto-hit! {damage} force damage!")
                if target.current_hp <= 0:
                    print(f"    -> {target.name} is SLAIN!")
                tracker.next_turn()
                continue
            elif "Marcus" in current.name:
                print(f"  {current.name} casts Bless on the party! (+1 attack/saves)")
                tracker.next_turn()
                continue

        # Make attack
        result = tracker.make_attack(current, target)

        # Narrate
        team_label = "" if is_player else "[Enemy] "
        print(f"  {team_label}{current.name} attacks {target.name}...")

        if result.critical_threat and result.critical_confirmed:
            print(f"    -> CRITICAL HIT! Rolled {result.attack_roll.total}")
            print(f"    -> {result.total_damage} damage!")
        elif result.hit:
            print(f"    -> Hit! Rolled {result.attack_roll.total} vs AC {target.armor_class}")
            print(f"    -> {result.total_damage} damage!")
        else:
            print(f"    -> Miss! Rolled {result.attack_roll.total} vs AC {target.armor_class}")

        if target.current_hp <= 0:
            status = "SLAIN" if target.combatant_type == CombatantType.ENEMY else "DOWN"
            print(f"    -> {target.name} is {status}!")
        elif target.current_hp < target.max_hp // 2:
            print(f"    -> {target.name} is bloodied! ({target.current_hp}/{target.max_hp} HP)")

        tracker.next_turn()

    # Final status
    print()
    print("=== COMBAT SUMMARY ===")
    print()
    print("Party Status:")
    for c in tracker.combatants:
        if c.combatant_type == CombatantType.PLAYER:
            status = "Alive" if c.current_hp > 0 else "DOWN!"
            pct = (c.current_hp / c.max_hp) * 100 if c.max_hp > 0 else 0
            bar_filled = int(pct / 10)
            bar = "#" * bar_filled + "-" * (10 - bar_filled)
            print(f"  {c.name}: {c.current_hp}/{c.max_hp} HP [{bar}] - {status}")

    print()
    print("Enemies:")
    killed = sum(1 for c in tracker.combatants if c.combatant_type == CombatantType.ENEMY and c.current_hp <= 0)
    total = sum(1 for c in tracker.combatants if c.combatant_type == CombatantType.ENEMY)
    print(f"  {killed}/{total} enemies defeated")

    for c in tracker.combatants:
        if c.combatant_type == CombatantType.ENEMY:
            if c.current_hp <= 0:
                print(f"    [X] {c.name} - DEAD")
            else:
                print(f"    [ ] {c.name} - {c.current_hp}/{c.max_hp} HP")

    print()
    print(f"Combat lasted {tracker.round_number} rounds")


if __name__ == "__main__":
    run_combat_test()
