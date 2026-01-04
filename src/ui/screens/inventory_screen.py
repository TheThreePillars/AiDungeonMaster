"""Inventory management screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from ...characters.inventory import Inventory, Item, ItemType, EquipmentSlot
from ...database.session import session_scope
from ...database.models import Character, InventoryItem


# Common starting items for quick-add
COMMON_ITEMS = {
    "Longsword": Item(
        name="Longsword", item_type=ItemType.WEAPON, weight=4.0, value=15,
        damage="1d8", damage_type="slashing", critical="19-20/x2",
        slot=EquipmentSlot.MAIN_HAND,
    ),
    "Shortsword": Item(
        name="Shortsword", item_type=ItemType.WEAPON, weight=2.0, value=10,
        damage="1d6", damage_type="piercing", critical="19-20/x2",
        slot=EquipmentSlot.MAIN_HAND,
    ),
    "Dagger": Item(
        name="Dagger", item_type=ItemType.WEAPON, weight=1.0, value=2,
        damage="1d4", damage_type="piercing", critical="19-20/x2",
        slot=EquipmentSlot.MAIN_HAND, range_increment=10,
    ),
    "Longbow": Item(
        name="Longbow", item_type=ItemType.WEAPON, weight=3.0, value=75,
        damage="1d8", damage_type="piercing", critical="x3",
        slot=EquipmentSlot.TWO_HANDS, range_increment=100,
    ),
    "Greataxe": Item(
        name="Greataxe", item_type=ItemType.WEAPON, weight=12.0, value=20,
        damage="1d12", damage_type="slashing", critical="x3",
        slot=EquipmentSlot.TWO_HANDS,
    ),
    "Quarterstaff": Item(
        name="Quarterstaff", item_type=ItemType.WEAPON, weight=4.0, value=0,
        damage="1d6", damage_type="bludgeoning", critical="x2",
        slot=EquipmentSlot.TWO_HANDS,
    ),
    "Chain Shirt": Item(
        name="Chain Shirt", item_type=ItemType.ARMOR, weight=25.0, value=100,
        ac_bonus=4, max_dex=4, armor_check_penalty=-2, spell_failure=20,
        slot=EquipmentSlot.ARMOR,
    ),
    "Leather Armor": Item(
        name="Leather Armor", item_type=ItemType.ARMOR, weight=15.0, value=10,
        ac_bonus=2, max_dex=6, armor_check_penalty=0, spell_failure=10,
        slot=EquipmentSlot.ARMOR,
    ),
    "Scale Mail": Item(
        name="Scale Mail", item_type=ItemType.ARMOR, weight=30.0, value=50,
        ac_bonus=5, max_dex=3, armor_check_penalty=-4, spell_failure=25,
        slot=EquipmentSlot.ARMOR,
    ),
    "Full Plate": Item(
        name="Full Plate", item_type=ItemType.ARMOR, weight=50.0, value=1500,
        ac_bonus=9, max_dex=1, armor_check_penalty=-6, spell_failure=35,
        slot=EquipmentSlot.ARMOR,
    ),
    "Light Shield": Item(
        name="Light Shield", item_type=ItemType.SHIELD, weight=6.0, value=9,
        ac_bonus=1, armor_check_penalty=-1, spell_failure=5,
        slot=EquipmentSlot.OFF_HAND,
    ),
    "Heavy Shield": Item(
        name="Heavy Shield", item_type=ItemType.SHIELD, weight=15.0, value=20,
        ac_bonus=2, armor_check_penalty=-2, spell_failure=15,
        slot=EquipmentSlot.OFF_HAND,
    ),
    "Potion of Cure Light Wounds": Item(
        name="Potion of Cure Light Wounds", item_type=ItemType.POTION,
        weight=0.1, value=50, is_magic=True, caster_level=1,
        description="Heals 1d8+1 HP when consumed.",
    ),
    "Potion of Cure Moderate Wounds": Item(
        name="Potion of Cure Moderate Wounds", item_type=ItemType.POTION,
        weight=0.1, value=300, is_magic=True, caster_level=3,
        description="Heals 2d8+3 HP when consumed.",
    ),
    "Rope (50 ft)": Item(
        name="Rope (50 ft)", item_type=ItemType.GEAR, weight=10.0, value=1,
    ),
    "Torch": Item(
        name="Torch", item_type=ItemType.GEAR, weight=1.0, value=0,
        description="Burns for 1 hour, provides 20 ft normal light.",
    ),
    "Backpack": Item(
        name="Backpack", item_type=ItemType.CONTAINER, weight=2.0, value=2,
    ),
    "Rations (1 day)": Item(
        name="Rations (1 day)", item_type=ItemType.GEAR, weight=1.0, value=0,
    ),
    "Arrows (20)": Item(
        name="Arrows (20)", item_type=ItemType.AMMUNITION, weight=3.0, value=1,
        quantity=20,
    ),
}


class InventoryScreen(Screen):
    """Screen for managing character inventory."""

    CSS = """
    InventoryScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }

    #inventory-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #details-panel {
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #inventory-table {
        height: 1fr;
    }

    #equipped-table {
        height: 10;
        margin-bottom: 1;
    }

    #item-details {
        height: 1fr;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
    }

    #weight-info {
        border: solid $warning;
        padding: 1;
        margin-bottom: 1;
    }

    #button-row {
        height: 3;
    }

    Button {
        margin-right: 1;
    }
    """

    def __init__(self, character_id: int | None = None):
        super().__init__()
        self.character_id = character_id
        self.inventory = Inventory()
        self.selected_item: Item | None = None
        self.character_strength = 10

    def compose(self) -> ComposeResult:
        with Container(id="inventory-panel"):
            yield Label("Inventory", classes="section-header")

            with TabbedContent():
                with TabPane("Items", id="tab-items"):
                    yield DataTable(id="inventory-table")
                with TabPane("Equipped", id="tab-equipped"):
                    yield DataTable(id="equipped-table")
                with TabPane("Add Item", id="tab-add"):
                    yield DataTable(id="shop-table")

            with Horizontal(id="button-row"):
                yield Button("Equip", id="btn-equip", variant="primary")
                yield Button("Unequip", id="btn-unequip")
                yield Button("Drop", id="btn-drop", variant="error")
                yield Button("Back", id="btn-back")

        with Container(id="details-panel"):
            yield Label("Item Details", classes="section-header")
            yield Static("Select an item to view details.", id="item-details")
            yield Static("", id="weight-info")

    def on_mount(self) -> None:
        """Set up tables and load inventory."""
        # Set up inventory table
        inv_table = self.query_one("#inventory-table", DataTable)
        inv_table.add_columns("Name", "Type", "Qty", "Wt", "Value")
        inv_table.cursor_type = "row"

        # Set up equipped table
        eq_table = self.query_one("#equipped-table", DataTable)
        eq_table.add_columns("Slot", "Item", "Stats")
        eq_table.cursor_type = "row"

        # Set up shop table
        shop_table = self.query_one("#shop-table", DataTable)
        shop_table.add_columns("Item", "Type", "Value")
        shop_table.cursor_type = "row"

        # Populate shop
        for name, item in COMMON_ITEMS.items():
            shop_table.add_row(name, item.item_type.value, f"{item.value} gp")

        # Load character inventory from database
        self._load_inventory()
        self._refresh_tables()

    def _load_inventory(self) -> None:
        """Load inventory from database."""
        if not self.character_id:
            # Use first character from game state
            if self.app.game_state.characters:
                self.character_id = self.app.game_state.characters[0].get("id")

        if not self.character_id:
            return

        try:
            with session_scope() as session:
                character = session.query(Character).filter_by(id=self.character_id).first()
                if character:
                    self.character_strength = character.strength

                    # Load inventory items
                    for db_item in character.inventory:
                        item = Item(
                            name=db_item.name,
                            item_type=ItemType(db_item.item_type),
                            weight=db_item.weight,
                            value=db_item.value,
                            quantity=db_item.quantity,
                            description=db_item.description or "",
                            equipped=db_item.equipped,
                            slot=EquipmentSlot(db_item.slot) if db_item.slot else EquipmentSlot.NONE,
                            is_magic=db_item.is_magic,
                            is_identified=db_item.is_identified,
                        )

                        # Parse properties JSON for weapon/armor stats
                        props = db_item.properties or {}
                        if item.item_type == ItemType.WEAPON:
                            item.damage = props.get("damage", "")
                            item.damage_type = props.get("damage_type", "")
                            item.critical = props.get("critical", "x2")
                        elif item.item_type in [ItemType.ARMOR, ItemType.SHIELD]:
                            item.ac_bonus = props.get("ac_bonus", 0)
                            item.armor_check_penalty = props.get("armor_check_penalty", 0)

                        self.inventory.add_item(item)
                        if item.equipped:
                            self.inventory.equipped[item.slot] = item

        except Exception as e:
            self.app.notify(f"Error loading inventory: {e}", title="Error", severity="error")

    def _save_inventory(self) -> None:
        """Save inventory to database."""
        if not self.character_id:
            return

        try:
            with session_scope() as session:
                character = session.query(Character).filter_by(id=self.character_id).first()
                if not character:
                    return

                # Clear existing inventory
                for item in character.inventory:
                    session.delete(item)

                # Add current inventory
                for item in self.inventory.items:
                    props = {}
                    if item.item_type == ItemType.WEAPON:
                        props = {
                            "damage": item.damage,
                            "damage_type": item.damage_type,
                            "critical": item.critical,
                        }
                    elif item.item_type in [ItemType.ARMOR, ItemType.SHIELD]:
                        props = {
                            "ac_bonus": item.ac_bonus,
                            "armor_check_penalty": item.armor_check_penalty,
                            "spell_failure": item.spell_failure,
                        }

                    db_item = InventoryItem(
                        character_id=self.character_id,
                        name=item.name,
                        item_type=item.item_type.value,
                        weight=item.weight,
                        value=item.value,
                        quantity=item.quantity,
                        description=item.description,
                        equipped=item.equipped,
                        slot=item.slot.value if item.slot != EquipmentSlot.NONE else None,
                        is_magic=item.is_magic,
                        is_identified=item.is_identified,
                        properties=props,
                    )
                    session.add(db_item)

        except Exception as e:
            self.app.notify(f"Error saving inventory: {e}", title="Error", severity="error")

    def _refresh_tables(self) -> None:
        """Refresh all inventory tables."""
        # Refresh main inventory
        inv_table = self.query_one("#inventory-table", DataTable)
        inv_table.clear()

        for item in self.inventory.items:
            equipped_mark = "*" if item.equipped else ""
            inv_table.add_row(
                f"{item.display_name}{equipped_mark}",
                item.item_type.value[:6],
                str(item.quantity),
                f"{item.total_weight:.1f}",
                f"{item.total_value}g",
            )

        # Refresh equipped table
        eq_table = self.query_one("#equipped-table", DataTable)
        eq_table.clear()

        slot_names = {
            EquipmentSlot.ARMOR: "Armor",
            EquipmentSlot.MAIN_HAND: "Main Hand",
            EquipmentSlot.OFF_HAND: "Off Hand",
            EquipmentSlot.TWO_HANDS: "Two Hands",
            EquipmentSlot.HEAD: "Head",
            EquipmentSlot.NECK: "Neck",
            EquipmentSlot.RING_LEFT: "Ring (L)",
            EquipmentSlot.RING_RIGHT: "Ring (R)",
        }

        for slot, name in slot_names.items():
            item = self.inventory.equipped.get(slot)
            if item:
                stats = self._get_item_stats_brief(item)
                eq_table.add_row(name, item.display_name, stats)
            else:
                eq_table.add_row(name, "(empty)", "-")

        # Update weight info
        self._update_weight_info()

    def _get_item_stats_brief(self, item: Item) -> str:
        """Get brief stats string for an item."""
        if item.item_type == ItemType.WEAPON:
            return f"{item.damage} {item.damage_type[:3]}"
        elif item.item_type in [ItemType.ARMOR, ItemType.SHIELD]:
            return f"AC +{item.ac_bonus}"
        return "-"

    def _update_weight_info(self) -> None:
        """Update weight and encumbrance display."""
        weight_info = self.query_one("#weight-info", Static)

        total_weight = self.inventory.get_total_weight()
        capacity = self.inventory.get_carrying_capacity(self.character_strength)
        encumbrance = self.inventory.get_encumbrance(self.character_strength)

        weight_info.update(f"""[bold]Encumbrance:[/bold] {encumbrance.title()}
Total Weight: {total_weight:.1f} lbs
Light Load: < {capacity['light']:.0f} lbs
Medium Load: < {capacity['medium']:.0f} lbs
Heavy Load: < {capacity['heavy']:.0f} lbs

Total Value: {self.inventory.get_total_value()} gp""")

    def _update_item_details(self, item: Item) -> None:
        """Update item details panel."""
        details = self.query_one("#item-details", Static)

        text = f"[bold]{item.display_name}[/bold]\n"
        text += f"Type: {item.item_type.value}\n"
        text += f"Weight: {item.weight} lbs | Value: {item.value} gp\n\n"

        if item.item_type == ItemType.WEAPON:
            text += f"[bold]Weapon Stats:[/bold]\n"
            text += f"  Damage: {item.damage} ({item.damage_type})\n"
            text += f"  Critical: {item.critical}\n"
            if item.range_increment:
                text += f"  Range: {item.range_increment} ft\n"

        elif item.item_type in [ItemType.ARMOR, ItemType.SHIELD]:
            text += f"[bold]Armor Stats:[/bold]\n"
            text += f"  AC Bonus: +{item.ac_bonus}\n"
            if item.max_dex is not None:
                text += f"  Max Dex: +{item.max_dex}\n"
            text += f"  Check Penalty: {item.armor_check_penalty}\n"
            text += f"  Spell Failure: {item.spell_failure}%\n"

        if item.is_magic:
            text += f"\n[magenta]Magic Item[/magenta]\n"
            if item.enhancement:
                text += f"Enhancement: +{item.enhancement}\n"

        if item.description:
            text += f"\n{item.description}"

        details.update(text)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle item selection."""
        table_id = event.data_table.id

        if table_id == "inventory-table":
            if event.cursor_row < len(self.inventory.items):
                self.selected_item = self.inventory.items[event.cursor_row]
                self._update_item_details(self.selected_item)

        elif table_id == "shop-table":
            items_list = list(COMMON_ITEMS.values())
            if event.cursor_row < len(items_list):
                item = items_list[event.cursor_row]
                self._update_item_details(item)
                # Add to inventory on selection from shop
                self._add_item_copy(item)

    def _add_item_copy(self, template: Item) -> None:
        """Add a copy of an item to inventory."""
        import copy
        new_item = copy.deepcopy(template)
        new_item.equipped = False
        self.inventory.add_item(new_item)
        self._refresh_tables()
        self._save_inventory()
        self.app.notify(f"Added {new_item.name} to inventory.", title="Inventory")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-equip":
            self._equip_selected()
        elif button_id == "btn-unequip":
            self._unequip_selected()
        elif button_id == "btn-drop":
            self._drop_selected()
        elif button_id == "btn-back":
            self._save_inventory()
            self.app.pop_screen()

    def _equip_selected(self) -> None:
        """Equip the selected item."""
        if not self.selected_item:
            self.app.notify("Select an item first.", title="Inventory")
            return

        if self.selected_item.slot == EquipmentSlot.NONE:
            self.app.notify("This item cannot be equipped.", title="Inventory")
            return

        if self.inventory.equip(self.selected_item):
            self._refresh_tables()
            self._save_inventory()
            self.app.notify(f"Equipped {self.selected_item.name}.", title="Inventory")
        else:
            self.app.notify("Could not equip item.", title="Inventory")

    def _unequip_selected(self) -> None:
        """Unequip the selected item."""
        if not self.selected_item:
            self.app.notify("Select an item first.", title="Inventory")
            return

        if not self.selected_item.equipped:
            self.app.notify("Item is not equipped.", title="Inventory")
            return

        if self.inventory.unequip(self.selected_item):
            self._refresh_tables()
            self._save_inventory()
            self.app.notify(f"Unequipped {self.selected_item.name}.", title="Inventory")

    def _drop_selected(self) -> None:
        """Drop the selected item."""
        if not self.selected_item:
            self.app.notify("Select an item first.", title="Inventory")
            return

        name = self.selected_item.name
        if self.inventory.remove_item(self.selected_item):
            self.selected_item = None
            self._refresh_tables()
            self._save_inventory()
            self.app.notify(f"Dropped {name}.", title="Inventory")
