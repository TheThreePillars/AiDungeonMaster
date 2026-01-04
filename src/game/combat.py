"""Combat tracker and initiative management for Pathfinder 1e."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .dice import DiceRoller
from .rules import AttackResult, CheckResult, DamageType, RulesEngine


class CombatantType(Enum):
    """Type of combatant."""

    PLAYER = "player"
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


class CombatState(Enum):
    """State of combat."""

    NOT_STARTED = "not_started"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass
class Combatant:
    """A participant in combat."""

    name: str
    combatant_type: CombatantType
    initiative: int = 0
    initiative_modifier: int = 0

    # Combat stats
    max_hp: int = 1
    current_hp: int = 1
    temp_hp: int = 0
    armor_class: int = 10
    touch_ac: int = 10
    flat_footed_ac: int = 10
    cmb: int = 0
    cmd: int = 10

    # Attack info
    attack_bonus: int = 0
    damage_dice: str = "1d4"
    damage_bonus: int = 0
    damage_type: DamageType = DamageType.BLUDGEONING

    # Status
    conditions: list[str] = field(default_factory=list)
    is_active: bool = True
    has_acted: bool = False

    # For tracking character/NPC reference
    character_id: int | None = None
    npc_id: int | None = None

    # Notes
    notes: str = ""

    @property
    def is_conscious(self) -> bool:
        """Check if combatant is conscious."""
        return self.current_hp > 0

    @property
    def is_dying(self) -> bool:
        """Check if combatant is dying."""
        return self.current_hp < 0 and self.current_hp > -10

    @property
    def is_dead(self) -> bool:
        """Check if combatant is dead."""
        return self.current_hp <= -10

    @property
    def hp_status(self) -> str:
        """Get HP status description."""
        if self.is_dead:
            return "Dead"
        elif self.is_dying:
            return "Dying"
        elif self.current_hp == 0:
            return "Disabled"
        elif self.current_hp < self.max_hp * 0.25:
            return "Critical"
        elif self.current_hp < self.max_hp * 0.5:
            return "Bloodied"
        else:
            return "Healthy"

    def take_damage(self, amount: int, nonlethal: bool = False) -> int:
        """Apply damage to the combatant.

        Args:
            amount: Damage amount
            nonlethal: Whether damage is nonlethal

        Returns:
            Actual damage dealt
        """
        if nonlethal:
            # Nonlethal tracked separately in full implementation
            return amount

        # Temp HP absorbs first
        if self.temp_hp > 0:
            absorbed = min(self.temp_hp, amount)
            self.temp_hp -= absorbed
            amount -= absorbed

        old_hp = self.current_hp
        self.current_hp -= amount
        return old_hp - self.current_hp

    def heal(self, amount: int) -> int:
        """Heal the combatant.

        Args:
            amount: Healing amount

        Returns:
            Actual amount healed
        """
        old_hp = self.current_hp
        self.current_hp = min(self.current_hp + amount, self.max_hp)
        return self.current_hp - old_hp

    def add_condition(self, condition: str) -> None:
        """Add a condition."""
        if condition.lower() not in [c.lower() for c in self.conditions]:
            self.conditions.append(condition)

    def remove_condition(self, condition: str) -> None:
        """Remove a condition."""
        self.conditions = [c for c in self.conditions if c.lower() != condition.lower()]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.combatant_type.value,
            "initiative": self.initiative,
            "initiative_modifier": self.initiative_modifier,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "temp_hp": self.temp_hp,
            "armor_class": self.armor_class,
            "touch_ac": self.touch_ac,
            "flat_footed_ac": self.flat_footed_ac,
            "cmb": self.cmb,
            "cmd": self.cmd,
            "attack_bonus": self.attack_bonus,
            "damage_dice": self.damage_dice,
            "damage_bonus": self.damage_bonus,
            "damage_type": self.damage_type.value,
            "conditions": self.conditions,
            "is_active": self.is_active,
            "character_id": self.character_id,
            "npc_id": self.npc_id,
            "notes": self.notes,
        }


@dataclass
class CombatAction:
    """A recorded combat action."""

    round_number: int
    actor: str
    action_type: str  # attack, spell, move, etc.
    target: str | None
    description: str
    result: str
    damage_dealt: int = 0
    healing_done: int = 0


class CombatTracker:
    """Manages combat encounters."""

    def __init__(self):
        """Initialize combat tracker."""
        self.combatants: list[Combatant] = []
        self.initiative_order: list[Combatant] = []
        self.current_turn: int = 0
        self.round_number: int = 0
        self.state: CombatState = CombatState.NOT_STARTED
        self.combat_log: list[CombatAction] = []

        self.rules = RulesEngine()
        self.roller = DiceRoller()

        # Callbacks for UI integration
        self.on_turn_change: Callable[[Combatant], None] | None = None
        self.on_round_change: Callable[[int], None] | None = None
        self.on_combatant_update: Callable[[Combatant], None] | None = None

    def add_combatant(self, combatant: Combatant) -> None:
        """Add a combatant to the encounter.

        Args:
            combatant: Combatant to add
        """
        self.combatants.append(combatant)

        if self.state == CombatState.ACTIVE:
            # Roll initiative and insert into order
            init_result = self.rules.roll_initiative(combatant.initiative_modifier)
            combatant.initiative = init_result.total
            self._insert_into_initiative(combatant)

    def remove_combatant(self, combatant: Combatant) -> None:
        """Remove a combatant from the encounter.

        Args:
            combatant: Combatant to remove
        """
        if combatant in self.combatants:
            self.combatants.remove(combatant)
        if combatant in self.initiative_order:
            # Adjust current turn if needed
            current_index = self.initiative_order.index(combatant)
            if current_index <= self.current_turn and self.current_turn > 0:
                self.current_turn -= 1
            self.initiative_order.remove(combatant)

    def start_combat(self) -> None:
        """Start combat and roll initiative for all combatants."""
        if self.state != CombatState.NOT_STARTED:
            return

        # Roll initiative for everyone
        for combatant in self.combatants:
            init_result = self.rules.roll_initiative(combatant.initiative_modifier)
            combatant.initiative = init_result.total

        # Sort by initiative (descending), with dex mod as tiebreaker
        self.initiative_order = sorted(
            self.combatants,
            key=lambda c: (c.initiative, c.initiative_modifier),
            reverse=True,
        )

        self.current_turn = 0
        self.round_number = 1
        self.state = CombatState.ACTIVE

        # Reset acted flags
        for combatant in self.combatants:
            combatant.has_acted = False

        if self.on_round_change:
            self.on_round_change(self.round_number)

        if self.initiative_order and self.on_turn_change:
            self.on_turn_change(self.initiative_order[0])

    def end_combat(self) -> None:
        """End the current combat."""
        self.state = CombatState.ENDED

    def pause_combat(self) -> None:
        """Pause combat."""
        if self.state == CombatState.ACTIVE:
            self.state = CombatState.PAUSED

    def resume_combat(self) -> None:
        """Resume paused combat."""
        if self.state == CombatState.PAUSED:
            self.state = CombatState.ACTIVE

    def get_current_combatant(self) -> Combatant | None:
        """Get the combatant whose turn it is.

        Returns:
            Current combatant or None
        """
        if not self.initiative_order or self.state != CombatState.ACTIVE:
            return None

        return self.initiative_order[self.current_turn]

    def next_turn(self) -> Combatant | None:
        """Advance to the next turn.

        Returns:
            The new current combatant
        """
        if self.state != CombatState.ACTIVE or not self.initiative_order:
            return None

        # Mark current combatant as having acted
        current = self.get_current_combatant()
        if current:
            current.has_acted = True

        # Find next active combatant
        original_turn = self.current_turn
        while True:
            self.current_turn = (self.current_turn + 1) % len(self.initiative_order)

            # Check if we've gone through everyone (new round)
            if self.current_turn == 0:
                self.round_number += 1
                for combatant in self.combatants:
                    combatant.has_acted = False
                if self.on_round_change:
                    self.on_round_change(self.round_number)

            next_combatant = self.initiative_order[self.current_turn]

            # Skip inactive combatants
            if next_combatant.is_active and next_combatant.is_conscious:
                break

            # Prevent infinite loop if all combatants are inactive
            if self.current_turn == original_turn:
                return None

        if self.on_turn_change:
            self.on_turn_change(next_combatant)

        return next_combatant

    def delay_turn(self, new_initiative: int) -> None:
        """Delay the current combatant's turn.

        Args:
            new_initiative: New initiative count to act on
        """
        current = self.get_current_combatant()
        if not current:
            return

        # Remove from current position
        self.initiative_order.remove(current)

        # Set new initiative
        current.initiative = new_initiative

        # Reinsert at new position
        self._insert_into_initiative(current)

        # Adjust current turn index
        self.current_turn = self.initiative_order.index(current)

    def ready_action(self, combatant: Combatant) -> None:
        """Mark a combatant as readying an action.

        Args:
            combatant: Combatant readying action
        """
        combatant.add_condition("readying")

    def _insert_into_initiative(self, combatant: Combatant) -> None:
        """Insert a combatant into the initiative order.

        Args:
            combatant: Combatant to insert
        """
        for i, c in enumerate(self.initiative_order):
            if combatant.initiative > c.initiative:
                self.initiative_order.insert(i, combatant)
                return
            elif combatant.initiative == c.initiative:
                # Tiebreaker: higher initiative modifier goes first
                if combatant.initiative_modifier > c.initiative_modifier:
                    self.initiative_order.insert(i, combatant)
                    return

        # Add at end if lowest initiative
        self.initiative_order.append(combatant)

    def make_attack(
        self,
        attacker: Combatant,
        target: Combatant,
        attack_bonus_modifier: int = 0,
        damage_bonus_modifier: int = 0,
    ) -> AttackResult:
        """Make an attack from one combatant to another.

        Args:
            attacker: Attacking combatant
            target: Target combatant
            attack_bonus_modifier: Additional attack modifier
            damage_bonus_modifier: Additional damage modifier

        Returns:
            AttackResult with all details
        """
        total_attack = attacker.attack_bonus + attack_bonus_modifier
        total_damage_bonus = attacker.damage_bonus + damage_bonus_modifier

        result = self.rules.make_attack(
            attack_bonus=total_attack,
            target_ac=target.armor_class,
            damage_dice=attacker.damage_dice,
            damage_bonus=total_damage_bonus,
            damage_type=attacker.damage_type,
        )

        # Apply damage if hit
        if result.hit:
            target.take_damage(result.total_damage)
            if self.on_combatant_update:
                self.on_combatant_update(target)

        # Log the action
        self.log_action(
            actor=attacker.name,
            action_type="attack",
            target=target.name,
            description=f"{attacker.name} attacks {target.name}",
            result=str(result),
            damage_dealt=result.total_damage if result.hit else 0,
        )

        return result

    def apply_damage(self, target: Combatant, amount: int, source: str = "Unknown") -> None:
        """Apply damage to a combatant.

        Args:
            target: Target combatant
            amount: Damage amount
            source: Source of damage
        """
        actual_damage = target.take_damage(amount)

        self.log_action(
            actor=source,
            action_type="damage",
            target=target.name,
            description=f"{source} deals {amount} damage to {target.name}",
            result=f"{target.name} takes {actual_damage} damage ({target.current_hp}/{target.max_hp} HP)",
            damage_dealt=actual_damage,
        )

        if self.on_combatant_update:
            self.on_combatant_update(target)

    def apply_healing(self, target: Combatant, amount: int, source: str = "Unknown") -> None:
        """Apply healing to a combatant.

        Args:
            target: Target combatant
            amount: Healing amount
            source: Source of healing
        """
        actual_healing = target.heal(amount)

        self.log_action(
            actor=source,
            action_type="heal",
            target=target.name,
            description=f"{source} heals {target.name} for {amount}",
            result=f"{target.name} heals {actual_healing} HP ({target.current_hp}/{target.max_hp} HP)",
            healing_done=actual_healing,
        )

        if self.on_combatant_update:
            self.on_combatant_update(target)

    def log_action(
        self,
        actor: str,
        action_type: str,
        target: str | None,
        description: str,
        result: str,
        damage_dealt: int = 0,
        healing_done: int = 0,
    ) -> CombatAction:
        """Log a combat action.

        Args:
            actor: Name of actor
            action_type: Type of action
            target: Target of action
            description: Description of action
            result: Result of action
            damage_dealt: Damage dealt
            healing_done: Healing done

        Returns:
            The logged CombatAction
        """
        action = CombatAction(
            round_number=self.round_number,
            actor=actor,
            action_type=action_type,
            target=target,
            description=description,
            result=result,
            damage_dealt=damage_dealt,
            healing_done=healing_done,
        )
        self.combat_log.append(action)
        return action

    def get_combatants_by_type(self, combatant_type: CombatantType) -> list[Combatant]:
        """Get all combatants of a specific type.

        Args:
            combatant_type: Type to filter by

        Returns:
            List of matching combatants
        """
        return [c for c in self.combatants if c.combatant_type == combatant_type]

    def get_active_enemies(self) -> list[Combatant]:
        """Get all active enemy combatants."""
        return [
            c for c in self.combatants
            if c.combatant_type == CombatantType.ENEMY and c.is_active and c.is_conscious
        ]

    def get_active_players(self) -> list[Combatant]:
        """Get all active player combatants."""
        return [
            c for c in self.combatants
            if c.combatant_type == CombatantType.PLAYER and c.is_active and c.is_conscious
        ]

    def check_combat_end(self) -> str | None:
        """Check if combat should end.

        Returns:
            "victory", "defeat", or None if combat continues
        """
        active_players = self.get_active_players()
        active_enemies = self.get_active_enemies()

        if not active_enemies:
            return "victory"
        if not active_players:
            return "defeat"

        return None

    def get_initiative_display(self) -> list[dict[str, Any]]:
        """Get initiative order for display.

        Returns:
            List of combatant info dicts
        """
        display = []
        for i, combatant in enumerate(self.initiative_order):
            is_current = i == self.current_turn and self.state == CombatState.ACTIVE
            display.append({
                "name": combatant.name,
                "initiative": combatant.initiative,
                "hp": f"{combatant.current_hp}/{combatant.max_hp}",
                "status": combatant.hp_status,
                "type": combatant.combatant_type.value,
                "conditions": combatant.conditions,
                "is_current": is_current,
            })
        return display

    def to_dict(self) -> dict[str, Any]:
        """Convert combat state to dictionary for serialization."""
        return {
            "combatants": [c.to_dict() for c in self.combatants],
            "initiative_order": [c.name for c in self.initiative_order],
            "current_turn": self.current_turn,
            "round_number": self.round_number,
            "state": self.state.value,
            "combat_log": [
                {
                    "round": a.round_number,
                    "actor": a.actor,
                    "action_type": a.action_type,
                    "target": a.target,
                    "description": a.description,
                    "result": a.result,
                }
                for a in self.combat_log
            ],
        }
