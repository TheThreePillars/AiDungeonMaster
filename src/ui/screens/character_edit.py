"""Character editing screen for modifying character details."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from ...database.session import session_scope
from ...database.models import Character


ALIGNMENTS = [
    ("Lawful Good", "LG"),
    ("Neutral Good", "NG"),
    ("Chaotic Good", "CG"),
    ("Lawful Neutral", "LN"),
    ("True Neutral", "N"),
    ("Chaotic Neutral", "CN"),
    ("Lawful Evil", "LE"),
    ("Neutral Evil", "NE"),
    ("Chaotic Evil", "CE"),
]


class CharacterEditScreen(ModalScreen):
    """Modal screen for editing character details."""

    CSS = """
    CharacterEditScreen {
        align: center middle;
    }

    #edit-dialog {
        width: 70;
        height: 35;
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
        margin-bottom: 1;
    }

    .form-row {
        height: 3;
        margin-bottom: 1;
    }

    .form-label {
        width: 15;
    }

    Input {
        width: 1fr;
    }

    Select {
        width: 1fr;
    }

    #backstory-area {
        height: 6;
    }

    #scroll-area {
        height: 1fr;
    }

    #button-row {
        dock: bottom;
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    .ability-row {
        height: 1;
    }

    .ability-label {
        width: 6;
    }

    .ability-value {
        width: 4;
    }

    .ability-mod {
        width: 6;
        color: $text-muted;
    }
    """

    def __init__(self, character_id: int):
        """Initialize the character edit screen.

        Args:
            character_id: Database ID of the character to edit.
        """
        super().__init__()
        self.character_id = character_id
        self.character_data = {}
        self._load_character()

    def _load_character(self) -> None:
        """Load character data from database."""
        try:
            with session_scope() as session:
                char = session.query(Character).filter_by(id=self.character_id).first()
                if char:
                    self.character_data = {
                        "id": char.id,
                        "name": char.name,
                        "race": char.race,
                        "class": char.character_class,
                        "level": char.level,
                        "alignment": char.alignment or "",
                        "deity": char.deity or "",
                        "backstory": char.backstory or "",
                        "personality_traits": char.personality_traits or "",
                        "ideals": char.ideals or "",
                        "bonds": char.bonds or "",
                        "flaws": char.flaws or "",
                        "strength": char.strength,
                        "dexterity": char.dexterity,
                        "constitution": char.constitution,
                        "intelligence": char.intelligence,
                        "wisdom": char.wisdom,
                        "charisma": char.charisma,
                        "current_hp": char.current_hp,
                        "max_hp": char.max_hp,
                        "languages": char.languages or ["Common"],
                        "feats": char.feats or [],
                    }
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        with Container(id="edit-dialog"):
            yield Label(
                f"Edit Character: {self.character_data.get('name', 'Unknown')}",
                classes="header"
            )

            with VerticalScroll(id="scroll-area"):
                # Basic Info Section
                with Container(classes="section"):
                    yield Label("Basic Information", classes="section-title")

                    with Horizontal(classes="form-row"):
                        yield Label("Name:", classes="form-label")
                        yield Input(
                            value=self.character_data.get("name", ""),
                            id="input-name"
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Alignment:", classes="form-label")
                        current_alignment = self.character_data.get("alignment", "")
                        yield Select(
                            ALIGNMENTS,
                            id="select-alignment",
                            value=current_alignment if current_alignment else Select.BLANK,
                            prompt="Select alignment",
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Deity:", classes="form-label")
                        yield Input(
                            value=self.character_data.get("deity", ""),
                            id="input-deity",
                            placeholder="None"
                        )

                # Ability Scores (display only)
                with Container(classes="section"):
                    yield Label("Ability Scores", classes="section-title")

                    def mod_str(score: int) -> str:
                        m = (score - 10) // 2
                        return f"({m:+d})"

                    scores = [
                        ("STR", self.character_data.get("strength", 10)),
                        ("DEX", self.character_data.get("dexterity", 10)),
                        ("CON", self.character_data.get("constitution", 10)),
                        ("INT", self.character_data.get("intelligence", 10)),
                        ("WIS", self.character_data.get("wisdom", 10)),
                        ("CHA", self.character_data.get("charisma", 10)),
                    ]

                    for ability, score in scores:
                        with Horizontal(classes="ability-row"):
                            yield Label(f"{ability}:", classes="ability-label")
                            yield Label(str(score), classes="ability-value")
                            yield Label(mod_str(score), classes="ability-mod")

                # Languages Section
                with Container(classes="section"):
                    yield Label("Languages", classes="section-title")
                    languages = self.character_data.get("languages", ["Common"])
                    yield Input(
                        value=", ".join(languages),
                        id="input-languages",
                        placeholder="Common, Elvish, Draconic"
                    )
                    yield Label("(comma-separated)", classes="form-label")

                # Roleplay Section
                with Container(classes="section"):
                    yield Label("Roleplay", classes="section-title")

                    yield Label("Backstory:")
                    yield TextArea(
                        self.character_data.get("backstory", ""),
                        id="backstory-area"
                    )

                    with Horizontal(classes="form-row"):
                        yield Label("Personality:", classes="form-label")
                        yield Input(
                            value=self.character_data.get("personality_traits", ""),
                            id="input-personality"
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Ideals:", classes="form-label")
                        yield Input(
                            value=self.character_data.get("ideals", ""),
                            id="input-ideals"
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Bonds:", classes="form-label")
                        yield Input(
                            value=self.character_data.get("bonds", ""),
                            id="input-bonds"
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Flaws:", classes="form-label")
                        yield Input(
                            value=self.character_data.get("flaws", ""),
                            id="input-flaws"
                        )

                # HP Adjustment
                with Container(classes="section"):
                    yield Label("Hit Points", classes="section-title")
                    with Horizontal(classes="form-row"):
                        yield Label("Current HP:", classes="form-label")
                        yield Input(
                            value=str(self.character_data.get("current_hp", 1)),
                            id="input-current-hp"
                        )
                        yield Label(f"/ {self.character_data.get('max_hp', 1)}")

            with Horizontal(id="button-row"):
                yield Button("Save Changes", id="btn-save", variant="success")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-save":
            self._save_changes()
        elif button_id == "btn-cancel":
            self.dismiss(False)

    def _save_changes(self) -> None:
        """Save changes to the database."""
        try:
            # Gather form data
            name = self.query_one("#input-name", Input).value.strip()
            if not name:
                self.app.notify("Name cannot be empty.", title="Error", severity="error")
                return

            alignment_select = self.query_one("#select-alignment", Select)
            alignment = str(alignment_select.value) if alignment_select.value != Select.BLANK else None

            deity = self.query_one("#input-deity", Input).value.strip() or None

            languages_str = self.query_one("#input-languages", Input).value.strip()
            languages = [lang.strip() for lang in languages_str.split(",") if lang.strip()]
            if not languages:
                languages = ["Common"]

            backstory = self.query_one("#backstory-area", TextArea).text.strip() or None
            personality = self.query_one("#input-personality", Input).value.strip() or None
            ideals = self.query_one("#input-ideals", Input).value.strip() or None
            bonds = self.query_one("#input-bonds", Input).value.strip() or None
            flaws = self.query_one("#input-flaws", Input).value.strip() or None

            current_hp_str = self.query_one("#input-current-hp", Input).value.strip()
            try:
                current_hp = int(current_hp_str)
                current_hp = max(0, min(current_hp, self.character_data.get("max_hp", 1)))
            except ValueError:
                current_hp = self.character_data.get("current_hp", 1)

            with session_scope() as session:
                char = session.query(Character).filter_by(id=self.character_id).first()
                if char:
                    char.name = name
                    char.alignment = alignment
                    char.deity = deity
                    char.languages = languages
                    char.backstory = backstory
                    char.personality_traits = personality
                    char.ideals = ideals
                    char.bonds = bonds
                    char.flaws = flaws
                    char.current_hp = current_hp

                    self.app.notify(f"Saved changes to {name}.", title="Character Edit")

            self.dismiss(True)

        except Exception as e:
            self.app.notify(f"Error saving: {e}", title="Error", severity="error")
