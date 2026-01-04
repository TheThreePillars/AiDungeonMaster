"""Inventory and equipment management for Pathfinder 1e characters."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemType(Enum):
    """Types of inventory items."""

    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    POTION = "potion"
    SCROLL = "scroll"
    WAND = "wand"
    RING = "ring"
    WONDROUS = "wondrous"
    GEAR = "gear"
    AMMUNITION = "ammunition"
    TOOL = "tool"
    CONTAINER = "container"
    MATERIAL = "material"
    OTHER = "other"


class EquipmentSlot(Enum):
    """Equipment slots for worn items."""

    HEAD = "head"
    HEADBAND = "headband"
    EYES = "eyes"
    NECK = "neck"
    SHOULDERS = "shoulders"
    CHEST = "chest"
    BODY = "body"
    ARMOR = "armor"
    BELT = "belt"
    WRISTS = "wrists"
    HANDS = "hands"
    RING_LEFT = "ring_left"
    RING_RIGHT = "ring_right"
    FEET = "feet"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HANDS = "two_hands"
    NONE = "none"


@dataclass
class Item:
    """A single inventory item."""

    name: str
    item_type: ItemType
    weight: float = 0.0
    value: int = 0  # In gold pieces
    quantity: int = 1
    description: str = ""

    # Equipment info
    equipped: bool = False
    slot: EquipmentSlot = EquipmentSlot.NONE

    # Weapon properties
    damage: str = ""
    damage_type: str = ""
    critical: str = "x2"
    range_increment: int = 0
    weapon_special: list[str] = field(default_factory=list)

    # Armor properties
    ac_bonus: int = 0
    max_dex: int | None = None
    armor_check_penalty: int = 0
    spell_failure: int = 0
    speed_30: int = 30
    speed_20: int = 20

    # Magic item properties
    is_magic: bool = False
    is_identified: bool = True
    enhancement: int = 0
    magic_properties: list[str] = field(default_factory=list)
    caster_level: int = 0
    aura: str = ""

    # Consumable properties
    charges: int | None = None
    max_charges: int | None = None

    # Custom properties
    properties: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def total_weight(self) -> float:
        """Get total weight including quantity."""
        return self.weight * self.quantity

    @property
    def total_value(self) -> int:
        """Get total value including quantity."""
        return self.value * self.quantity

    @property
    def display_name(self) -> str:
        """Get display name with enhancement if applicable."""
        if self.is_magic and self.enhancement > 0:
            return f"{self.name} +{self.enhancement}"
        return self.name

    def use_charge(self) -> bool:
        """Use a charge from a charged item.

        Returns:
            True if charge was used, False if no charges remain
        """
        if self.charges is None:
            return True  # Non-charged items always succeed

        if self.charges > 0:
            self.charges -= 1
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert item to dictionary for serialization."""
        return {
            "name": self.name,
            "item_type": self.item_type.value,
            "weight": self.weight,
            "value": self.value,
            "quantity": self.quantity,
            "description": self.description,
            "equipped": self.equipped,
            "slot": self.slot.value,
            "damage": self.damage,
            "damage_type": self.damage_type,
            "critical": self.critical,
            "range_increment": self.range_increment,
            "weapon_special": self.weapon_special,
            "ac_bonus": self.ac_bonus,
            "max_dex": self.max_dex,
            "armor_check_penalty": self.armor_check_penalty,
            "spell_failure": self.spell_failure,
            "is_magic": self.is_magic,
            "is_identified": self.is_identified,
            "enhancement": self.enhancement,
            "magic_properties": self.magic_properties,
            "caster_level": self.caster_level,
            "aura": self.aura,
            "charges": self.charges,
            "max_charges": self.max_charges,
            "properties": self.properties,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        """Create item from dictionary data."""
        return cls(
            name=data.get("name", "Unknown"),
            item_type=ItemType(data.get("item_type", "other")),
            weight=data.get("weight", 0.0),
            value=data.get("value", 0),
            quantity=data.get("quantity", 1),
            description=data.get("description", ""),
            equipped=data.get("equipped", False),
            slot=EquipmentSlot(data.get("slot", "none")),
            damage=data.get("damage", ""),
            damage_type=data.get("damage_type", ""),
            critical=data.get("critical", "x2"),
            range_increment=data.get("range_increment", 0),
            weapon_special=data.get("weapon_special", []),
            ac_bonus=data.get("ac_bonus", 0),
            max_dex=data.get("max_dex"),
            armor_check_penalty=data.get("armor_check_penalty", 0),
            spell_failure=data.get("spell_failure", 0),
            is_magic=data.get("is_magic", False),
            is_identified=data.get("is_identified", True),
            enhancement=data.get("enhancement", 0),
            magic_properties=data.get("magic_properties", []),
            caster_level=data.get("caster_level", 0),
            aura=data.get("aura", ""),
            charges=data.get("charges"),
            max_charges=data.get("max_charges"),
            properties=data.get("properties", {}),
            notes=data.get("notes", ""),
        )


class Inventory:
    """Character inventory management."""

    # Standard carrying capacity multipliers by size
    SIZE_MULTIPLIERS = {
        "Fine": 0.125,
        "Diminutive": 0.25,
        "Tiny": 0.5,
        "Small": 0.75,
        "Medium": 1.0,
        "Large": 2.0,
        "Huge": 4.0,
        "Gargantuan": 8.0,
        "Colossal": 16.0,
    }

    # Carrying capacity by strength score
    CARRY_CAPACITY = {
        1: 3, 2: 6, 3: 10, 4: 13, 5: 16,
        6: 20, 7: 23, 8: 26, 9: 30, 10: 33,
        11: 38, 12: 43, 13: 50, 14: 58, 15: 66,
        16: 76, 17: 86, 18: 100, 19: 116, 20: 133,
        21: 153, 22: 173, 23: 200, 24: 233, 25: 266,
        26: 306, 27: 346, 28: 400, 29: 466,
    }

    def __init__(self):
        """Initialize an empty inventory."""
        self.items: list[Item] = []
        self.equipped: dict[EquipmentSlot, Item | None] = {
            slot: None for slot in EquipmentSlot
        }

    def add_item(self, item: Item) -> None:
        """Add an item to inventory.

        Args:
            item: Item to add
        """
        # Check if stackable item already exists
        if item.quantity > 0 and not item.is_magic:
            for existing in self.items:
                if (
                    existing.name == item.name
                    and existing.item_type == item.item_type
                    and not existing.is_magic
                    and not existing.equipped
                ):
                    existing.quantity += item.quantity
                    return

        self.items.append(item)

    def remove_item(self, item: Item, quantity: int = 1) -> bool:
        """Remove an item or reduce its quantity.

        Args:
            item: Item to remove
            quantity: Amount to remove

        Returns:
            True if successful
        """
        if item not in self.items:
            return False

        if item.quantity <= quantity:
            if item.equipped:
                self.unequip(item)
            self.items.remove(item)
        else:
            item.quantity -= quantity

        return True

    def equip(self, item: Item, slot: EquipmentSlot | None = None) -> bool:
        """Equip an item.

        Args:
            item: Item to equip
            slot: Slot to equip to (uses item's default if not specified)

        Returns:
            True if successful
        """
        if item not in self.items:
            return False

        target_slot = slot or item.slot
        if target_slot == EquipmentSlot.NONE:
            return False

        # Handle two-handed weapons
        if target_slot == EquipmentSlot.TWO_HANDS:
            # Unequip both hands
            if self.equipped[EquipmentSlot.MAIN_HAND]:
                self.unequip(self.equipped[EquipmentSlot.MAIN_HAND])
            if self.equipped[EquipmentSlot.OFF_HAND]:
                self.unequip(self.equipped[EquipmentSlot.OFF_HAND])

        # Unequip existing item in slot
        if self.equipped.get(target_slot):
            self.unequip(self.equipped[target_slot])

        item.equipped = True
        item.slot = target_slot
        self.equipped[target_slot] = item
        return True

    def unequip(self, item: Item) -> bool:
        """Unequip an item.

        Args:
            item: Item to unequip

        Returns:
            True if successful
        """
        if not item.equipped:
            return False

        if self.equipped.get(item.slot) == item:
            self.equipped[item.slot] = None

        item.equipped = False
        return True

    def get_equipped_armor(self) -> Item | None:
        """Get currently equipped armor."""
        return self.equipped.get(EquipmentSlot.ARMOR)

    def get_equipped_shield(self) -> Item | None:
        """Get currently equipped shield."""
        return self.equipped.get(EquipmentSlot.OFF_HAND)

    def get_equipped_weapons(self) -> list[Item]:
        """Get all equipped weapons."""
        weapons = []
        for slot in [EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HANDS]:
            item = self.equipped.get(slot)
            if item and item.item_type == ItemType.WEAPON:
                weapons.append(item)
        return weapons

    def get_total_weight(self) -> float:
        """Calculate total inventory weight."""
        return sum(item.total_weight for item in self.items)

    def get_total_value(self) -> int:
        """Calculate total inventory value in gold."""
        return sum(item.total_value for item in self.items)

    def get_carrying_capacity(self, strength: int, size: str = "Medium") -> dict[str, float]:
        """Calculate carrying capacity.

        Args:
            strength: Character's strength score
            size: Character's size category

        Returns:
            Dict with light, medium, heavy load limits
        """
        # Get base capacity for strength
        if strength <= 0:
            base = 0
        elif strength <= 29:
            base = self.CARRY_CAPACITY.get(strength, 33)
        else:
            # For strength > 29, multiply by 4 for each 10 over 20
            base = self.CARRY_CAPACITY[20]
            extra = strength - 20
            while extra >= 10:
                base *= 4
                extra -= 10
            # Handle remaining points
            if extra > 0:
                multiplier = self.CARRY_CAPACITY.get(10 + extra, 33) / self.CARRY_CAPACITY[10]
                base *= multiplier

        # Apply size modifier
        multiplier = self.SIZE_MULTIPLIERS.get(size, 1.0)
        base *= multiplier

        return {
            "light": base / 3,
            "medium": base * 2 / 3,
            "heavy": base,
        }

    def get_encumbrance(self, strength: int, size: str = "Medium") -> str:
        """Determine current encumbrance level.

        Args:
            strength: Character's strength score
            size: Character's size category

        Returns:
            "light", "medium", "heavy", or "overloaded"
        """
        capacity = self.get_carrying_capacity(strength, size)
        current = self.get_total_weight()

        if current <= capacity["light"]:
            return "light"
        elif current <= capacity["medium"]:
            return "medium"
        elif current <= capacity["heavy"]:
            return "heavy"
        else:
            return "overloaded"

    def get_armor_check_penalty(self) -> int:
        """Get total armor check penalty from equipped items."""
        penalty = 0

        armor = self.get_equipped_armor()
        if armor:
            penalty += armor.armor_check_penalty

        shield = self.get_equipped_shield()
        if shield and shield.item_type == ItemType.SHIELD:
            penalty += shield.armor_check_penalty

        return penalty

    def get_spell_failure(self) -> int:
        """Get total arcane spell failure chance."""
        failure = 0

        armor = self.get_equipped_armor()
        if armor:
            failure += armor.spell_failure

        shield = self.get_equipped_shield()
        if shield and shield.item_type == ItemType.SHIELD:
            failure += shield.spell_failure

        return failure

    def find_items(self, name: str = "", item_type: ItemType | None = None) -> list[Item]:
        """Search for items in inventory.

        Args:
            name: Partial name match
            item_type: Filter by type

        Returns:
            List of matching items
        """
        results = []
        for item in self.items:
            if name and name.lower() not in item.name.lower():
                continue
            if item_type and item.item_type != item_type:
                continue
            results.append(item)
        return results

    def to_dict(self) -> dict[str, Any]:
        """Convert inventory to dictionary for serialization."""
        return {
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Inventory":
        """Create inventory from dictionary data."""
        inventory = cls()
        for item_data in data.get("items", []):
            item = Item.from_dict(item_data)
            inventory.items.append(item)
            if item.equipped and item.slot != EquipmentSlot.NONE:
                inventory.equipped[item.slot] = item
        return inventory
