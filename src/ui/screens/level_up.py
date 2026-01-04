"""Level up screen for character advancement."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Static

from ...characters.classes import CLASSES, ClassManager


class LevelUpScreen(ModalScreen):
    """Modal screen for leveling up a character."""

    CSS = """
    LevelUpScreen {
        align: center middle;
    }

    #level-up-dialog {
        width: 60;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    .header {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }

    .section {
        margin-bottom: 1;
        border: solid $secondary;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $secondary;
    }

    .stat-row {
        height: 1;
    }

    .stat-label {
        width: 20;
    }

    .stat-value {
        width: 10;
    }

    .stat-change {
        color: $success;
    }

    #hp-options {
        margin-top: 1;
    }

    #ability-increase {
        margin-top: 1;
    }

    #button-row {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    Select {
        width: 100%;
    }
    """

    def __init__(self, character_data: dict):
        """Initialize the level up screen.

        Args:
            character_data: Character data dict with id, name, class, level, etc.
        """
        super().__init__()
        self.character = character_data
        self.class_manager = ClassManager()
        self.current_level = character_data.get("level", 1)
        self.new_level = self.current_level + 1
        self.hp_choice = "average"
        self.ability_increase = None

        # Calculate stat changes
        self._calculate_changes()

    def _calculate_changes(self) -> None:
        """Calculate stat changes for the level up."""
        class_name = self.character.get("class", "Fighter")
        char_class = CLASSES.get(class_name)

        # HP
        hit_die = char_class.hit_die if char_class else 8
        self.hit_die = hit_die
        self.hp_average = (hit_die // 2) + 1
        self.hp_rolled = None

        # BAB
        old_bab = self.class_manager.get_bab_at_level(class_name, self.current_level)
        new_bab = self.class_manager.get_bab_at_level(class_name, self.new_level)
        self.bab_change = new_bab - old_bab

        # Saves
        old_saves = self.class_manager.get_saves_at_level(class_name, self.current_level)
        new_saves = self.class_manager.get_saves_at_level(class_name, self.new_level)
        self.save_changes = {
            "fortitude": new_saves["fortitude"] - old_saves["fortitude"],
            "reflex": new_saves["reflex"] - old_saves["reflex"],
            "will": new_saves["will"] - old_saves["will"],
        }

        # Skill points
        int_mod = (self.character.get("intelligence", 10) - 10) // 2
        base_skills = char_class.skill_ranks_per_level if char_class else 2
        is_human = self.character.get("race", "").lower() == "human"
        self.skill_points = max(1, base_skills + int_mod) + (1 if is_human else 0)

        # Ability score increase at 4, 8, 12, 16, 20
        self.gets_ability_increase = self.new_level in [4, 8, 12, 16, 20]

        # Feat at odd levels
        self.gets_feat = self.new_level % 2 == 1

    def compose(self) -> ComposeResult:
        with Container(id="level-up-dialog"):
            yield Label(
                f"Level Up: {self.character.get('name', 'Character')}",
                classes="header"
            )
            yield Label(
                f"Level {self.current_level} -> {self.new_level}",
                classes="header"
            )

            # HP Section
            with Container(classes="section"):
                yield Label("Hit Points", classes="section-title")
                yield Label(f"Hit Die: d{self.hit_die}")

                with Horizontal(id="hp-options"):
                    yield Button(
                        f"Take Average ({self.hp_average})",
                        id="btn-hp-average",
                        variant="primary"
                    )
                    yield Button("Roll", id="btn-hp-roll")

                yield Static(
                    f"HP Gain: +{self.hp_average} (average)",
                    id="hp-display"
                )

            # Stat Changes Section
            with Container(classes="section"):
                yield Label("Stat Changes", classes="section-title")

                with Horizontal(classes="stat-row"):
                    yield Label("BAB:", classes="stat-label")
                    yield Label(
                        f"+{self.bab_change}" if self.bab_change > 0 else "No change",
                        classes="stat-change"
                    )

                with Horizontal(classes="stat-row"):
                    yield Label("Fortitude:", classes="stat-label")
                    change = self.save_changes["fortitude"]
                    yield Label(
                        f"+{change}" if change > 0 else "No change",
                        classes="stat-change"
                    )

                with Horizontal(classes="stat-row"):
                    yield Label("Reflex:", classes="stat-label")
                    change = self.save_changes["reflex"]
                    yield Label(
                        f"+{change}" if change > 0 else "No change",
                        classes="stat-change"
                    )

                with Horizontal(classes="stat-row"):
                    yield Label("Will:", classes="stat-label")
                    change = self.save_changes["will"]
                    yield Label(
                        f"+{change}" if change > 0 else "No change",
                        classes="stat-change"
                    )

                with Horizontal(classes="stat-row"):
                    yield Label("Skill Points:", classes="stat-label")
                    yield Label(f"+{self.skill_points}", classes="stat-change")

            # Ability Score Increase (if applicable)
            if self.gets_ability_increase:
                with Container(classes="section", id="ability-increase"):
                    yield Label("Ability Score Increase (+1)", classes="section-title")
                    yield Select(
                        [
                            ("Strength", "STR"),
                            ("Dexterity", "DEX"),
                            ("Constitution", "CON"),
                            ("Intelligence", "INT"),
                            ("Wisdom", "WIS"),
                            ("Charisma", "CHA"),
                        ],
                        id="select-ability",
                        prompt="Choose ability to increase",
                    )

            # Feat notification
            if self.gets_feat:
                with Container(classes="section"):
                    yield Label("New Feat Available!", classes="section-title")
                    yield Label("Choose a feat from the character sheet after leveling.")

            with Horizontal(id="button-row"):
                yield Button("Confirm Level Up", id="btn-confirm", variant="success")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-hp-average":
            self.hp_choice = "average"
            self.hp_rolled = None
            hp_display = self.query_one("#hp-display", Static)
            hp_display.update(f"HP Gain: +{self.hp_average} (average)")

            # Update button variants
            self.query_one("#btn-hp-average", Button).variant = "primary"
            self.query_one("#btn-hp-roll", Button).variant = "default"

        elif button_id == "btn-hp-roll":
            from ...game.dice import DiceRoller
            roller = DiceRoller()
            result = roller.roll(f"1d{self.hit_die}")
            self.hp_rolled = max(1, result.total)  # Minimum 1 HP
            self.hp_choice = "roll"

            hp_display = self.query_one("#hp-display", Static)
            hp_display.update(f"HP Gain: +{self.hp_rolled} (rolled {result.total})")

            # Update button variants
            self.query_one("#btn-hp-average", Button).variant = "default"
            self.query_one("#btn-hp-roll", Button).variant = "primary"

        elif button_id == "btn-confirm":
            self._confirm_level_up()

        elif button_id == "btn-cancel":
            self.dismiss(None)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle ability selection."""
        if event.select.id == "select-ability":
            self.ability_increase = str(event.value)

    def _confirm_level_up(self) -> None:
        """Confirm and apply the level up."""
        # Validate ability increase if required
        if self.gets_ability_increase and not self.ability_increase:
            self.app.notify(
                "Please choose an ability to increase.",
                title="Level Up",
                severity="error"
            )
            return

        # Calculate HP gain
        con_mod = (self.character.get("constitution", 10) - 10) // 2
        if self.hp_choice == "roll" and self.hp_rolled:
            hp_gain = self.hp_rolled + con_mod
        else:
            hp_gain = self.hp_average + con_mod

        hp_gain = max(1, hp_gain)  # Minimum 1 HP per level

        # Build result
        result = {
            "new_level": self.new_level,
            "hp_gain": hp_gain,
            "bab_change": self.bab_change,
            "save_changes": self.save_changes,
            "skill_points": self.skill_points,
            "ability_increase": self.ability_increase,
            "gets_feat": self.gets_feat,
        }

        self.dismiss(result)
