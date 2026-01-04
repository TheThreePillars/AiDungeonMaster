"""Character creation screen for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    OptionList,
    Select,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option

from ...characters.races import RACES
from ...characters.classes import CLASSES
from ...database.session import session_scope
from ...database.models import Character, Party
from .point_buy import PointBuyScreen


class AbilityScoreDisplay(Static):
    """Display for ability scores during character creation."""

    def __init__(self, **kwargs):
        """Initialize ability score display."""
        super().__init__(**kwargs)
        self.scores = {
            "STR": 10,
            "DEX": 10,
            "CON": 10,
            "INT": 10,
            "WIS": 10,
            "CHA": 10,
        }

    def compose(self) -> ComposeResult:
        """Compose the ability score display."""
        yield Label("Ability Scores", classes="section-header")
        for ability in self.scores:
            with Horizontal(classes="ability-row"):
                yield Label(f"{ability}:", classes="ability-label")
                yield Label(str(self.scores[ability]), id=f"score-{ability.lower()}")
                yield Label(self._get_modifier(self.scores[ability]), id=f"mod-{ability.lower()}")

    def _get_modifier(self, score: int) -> str:
        """Get modifier string for a score."""
        mod = (score - 10) // 2
        return f"({mod:+d})"

    def update_score(self, ability: str, value: int) -> None:
        """Update an ability score."""
        self.scores[ability.upper()] = value
        label = self.query_one(f"#score-{ability.lower()}", Label)
        label.update(str(value))
        mod_label = self.query_one(f"#mod-{ability.lower()}", Label)
        mod_label.update(self._get_modifier(value))


class CharacterCreationScreen(Screen):
    """Character creation wizard screen."""

    CSS = """
    CharacterCreationScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        padding: 1;
    }

    #left-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #right-panel {
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .form-group {
        margin-bottom: 1;
    }

    .form-label {
        margin-bottom: 0;
    }

    Input {
        margin-bottom: 1;
    }

    Select {
        width: 100%;
        margin-bottom: 1;
    }

    .ability-row {
        height: 1;
        margin-bottom: 0;
    }

    .ability-label {
        width: 5;
    }

    #preview-area {
        height: 1fr;
        border: solid $accent;
        padding: 1;
        overflow-y: auto;
    }

    #button-row {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self):
        """Initialize the character creation screen."""
        super().__init__()
        self.character_data = {
            "name": "",
            "race": "",
            "class": "",
            "background": "",
            "abilities": {},
        }

    def compose(self) -> ComposeResult:
        """Compose the character creation screen."""
        with Container(id="left-panel"):
            yield Label("Create Your Character", classes="section-header")

            with Vertical(classes="form-group"):
                yield Label("Name:", classes="form-label")
                yield Input(placeholder="Enter character name", id="input-name")

            with Vertical(classes="form-group"):
                yield Label("Race:", classes="form-label")
                yield Select(
                    [(race, race) for race in RACES.keys()],
                    id="select-race",
                    prompt="Select a race",
                )

            with Vertical(classes="form-group"):
                yield Label("Class:", classes="form-label")
                yield Select(
                    [(cls, cls) for cls in CLASSES.keys()],
                    id="select-class",
                    prompt="Select a class",
                )

            yield AbilityScoreDisplay(id="ability-display")

            with Horizontal(id="button-row"):
                yield Button("Roll Abilities", id="btn-roll", variant="primary")
                yield Button("Point Buy", id="btn-point-buy")
                yield Button("Create", id="btn-create", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="error")

        with Container(id="right-panel"):
            yield Label("Character Preview", classes="section-header")
            yield Static(id="preview-area")
            yield Label("Race Info", classes="section-header")
            yield Static(id="race-info")
            yield Label("Class Info", classes="section-header")
            yield Static(id="class-info")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "input-name":
            self.character_data["name"] = event.value
            self._update_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "select-race":
            self.character_data["race"] = str(event.value)
            self._update_race_info()
            self._update_preview()
        elif event.select.id == "select-class":
            self.character_data["class"] = str(event.value)
            self._update_class_info()
            self._update_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-roll":
            self._roll_abilities()
        elif button_id == "btn-point-buy":
            self._open_point_buy()
        elif button_id == "btn-create":
            self._create_character()
        elif button_id == "btn-cancel":
            self.app.pop_screen()

    def _roll_abilities(self) -> None:
        """Roll ability scores using 4d6 drop lowest."""
        from ...game.dice import DiceRoller

        roller = DiceRoller()
        display = self.query_one("#ability-display", AbilityScoreDisplay)

        for ability in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
            result = roller.roll("4d6 drop lowest")
            display.update_score(ability, result.total)
            self.character_data["abilities"][ability] = result.total

        self._update_preview()
        self.app.notify("Abilities rolled!", title="Dice")

    def _open_point_buy(self) -> None:
        """Open the point buy screen."""
        self.app.push_screen(PointBuyScreen(), self._handle_point_buy_result)

    def _handle_point_buy_result(self, scores: dict | None) -> None:
        """Handle the result from point buy screen."""
        if scores is None:
            return  # User cancelled

        display = self.query_one("#ability-display", AbilityScoreDisplay)

        for ability, score in scores.items():
            display.update_score(ability, score)
            self.character_data["abilities"][ability] = score

        self._update_preview()
        self.app.notify("Ability scores set!", title="Point Buy")

    def _update_preview(self) -> None:
        """Update the character preview."""
        preview = self.query_one("#preview-area", Static)

        name = self.character_data.get("name", "Unnamed")
        race = self.character_data.get("race", "Unknown")
        cls = self.character_data.get("class", "Unknown")

        text = f"""Name: {name}
Race: {race}
Class: {cls}

Ability Scores:"""

        for ability, score in self.character_data.get("abilities", {}).items():
            mod = (score - 10) // 2
            text += f"\n  {ability}: {score} ({mod:+d})"

        preview.update(text)

    def _update_race_info(self) -> None:
        """Update race information display."""
        race_info = self.query_one("#race-info", Static)
        race_name = self.character_data.get("race", "")

        if race_name and race_name in RACES:
            race = RACES[race_name]
            text = f"""Size: {race.size}
Speed: {race.speed} ft

Ability Modifiers:"""
            for ability, mod in race.ability_modifiers.items():
                text += f"\n  {ability}: {mod:+d}"

            if race.traits:
                text += "\n\nTraits:"
                for trait in race.traits[:3]:
                    text += f"\n  - {trait}"

            race_info.update(text)
        else:
            race_info.update("Select a race to see details.")

    def _update_class_info(self) -> None:
        """Update class information display."""
        class_info = self.query_one("#class-info", Static)
        class_name = self.character_data.get("class", "")

        if class_name and class_name in CLASSES:
            cls = CLASSES[class_name]
            text = f"""Hit Die: d{cls.hit_die}
BAB: {cls.bab_progression}
Skills/Level: {cls.skill_ranks_per_level}

Good Saves: {', '.join(cls.good_saves)}
Class Skills: {', '.join(cls.class_skills[:5])}..."""
            class_info.update(text)
        else:
            class_info.update("Select a class to see details.")

    def _create_character(self) -> None:
        """Create the character and save to database."""
        if not self.character_data.get("name"):
            self.app.notify("Please enter a name.", title="Error", severity="error")
            return
        if not self.character_data.get("race"):
            self.app.notify("Please select a race.", title="Error", severity="error")
            return
        if not self.character_data.get("class"):
            self.app.notify("Please select a class.", title="Error", severity="error")
            return
        if not self.character_data.get("abilities"):
            self.app.notify("Please roll abilities.", title="Error", severity="error")
            return

        try:
            # Get race and class data
            race_name = self.character_data["race"]
            class_name = self.character_data["class"]
            race = RACES.get(race_name)
            char_class = CLASSES.get(class_name)

            if not race or not char_class:
                self.app.notify("Invalid race or class.", title="Error", severity="error")
                return

            # Calculate ability scores with racial modifiers
            abilities = self.character_data["abilities"].copy()
            for ability, mod in race.ability_modifiers.items():
                if ability != "any":
                    ability_key = ability.upper()
                    if ability_key in abilities:
                        abilities[ability_key] += mod

            # Calculate initial HP (max at level 1 + CON modifier)
            con_mod = (abilities.get("CON", 10) - 10) // 2
            max_hp = char_class.hit_die + con_mod
            max_hp = max(1, max_hp)  # Minimum 1 HP

            # Calculate AC (10 + DEX modifier)
            dex_mod = (abilities.get("DEX", 10) - 10) // 2
            armor_class = 10 + dex_mod

            # Size modifier for Small races
            size_mod = 1 if race.size == "Small" else 0
            armor_class += size_mod

            with session_scope() as session:
                # Create a default party for the character if none exists
                party = session.query(Party).first()
                if not party:
                    party = Party(name="Adventuring Party")
                    session.add(party)
                    session.flush()

                # Create the character
                character = Character(
                    name=self.character_data["name"],
                    race=race_name,
                    character_class=class_name,
                    classes={class_name: 1},
                    level=1,
                    size=race.size,
                    party_id=party.id,
                    # Ability scores
                    strength=abilities.get("STR", 10),
                    dexterity=abilities.get("DEX", 10),
                    constitution=abilities.get("CON", 10),
                    intelligence=abilities.get("INT", 10),
                    wisdom=abilities.get("WIS", 10),
                    charisma=abilities.get("CHA", 10),
                    # Combat stats
                    max_hp=max_hp,
                    current_hp=max_hp,
                    armor_class=armor_class,
                    touch_ac=10 + dex_mod + size_mod,
                    flat_footed_ac=10 + size_mod,
                    base_attack_bonus=0,
                    speed=race.speed,
                    # Saves (base at level 1)
                    fortitude_base=2 if "fortitude" in char_class.good_saves else 0,
                    reflex_base=2 if "reflex" in char_class.good_saves else 0,
                    will_base=2 if "will" in char_class.good_saves else 0,
                    # Languages
                    languages=list(race.languages) if hasattr(race, 'languages') and race.languages else ["Common"],
                    # Starting gold (average for class)
                    gold=char_class.hit_die * 10,
                )

                session.add(character)
                session.flush()

                # Update game state with the new character
                self.app.game_state.party_id = party.id
                self.app.game_state.characters.append({
                    "id": character.id,
                    "name": character.name,
                    "race": character.race,
                    "class": character.character_class,
                    "level": character.level,
                    "current_hp": character.current_hp,
                    "max_hp": character.max_hp,
                    "ac": character.armor_class,
                })

            self.app.notify(
                f"Created {self.character_data['name']}!",
                title="Character Created",
            )
            self.app.pop_screen()

        except Exception as e:
            self.app.notify(f"Error creating character: {e}", title="Error", severity="error")
