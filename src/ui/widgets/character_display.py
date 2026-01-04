"""Character display widget for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, ProgressBar, Static

from ...characters.sheet import CharacterSheet


class HPBar(Static):
    """A health bar display widget."""

    CSS = """
    HPBar {
        height: 3;
        border: solid $error;
        padding: 0 1;
    }

    .hp-label {
        text-align: center;
    }

    ProgressBar {
        padding: 0;
    }

    ProgressBar > .bar--bar {
        color: $success;
    }
    """

    def __init__(self, current: int = 10, maximum: int = 10, **kwargs):
        """Initialize the HP bar."""
        super().__init__(**kwargs)
        self.current = current
        self.maximum = maximum

    def compose(self) -> ComposeResult:
        """Compose the HP bar."""
        yield Label(f"HP: {self.current}/{self.maximum}", id="hp-label", classes="hp-label")
        yield ProgressBar(total=self.maximum, show_eta=False, id="hp-bar")

    def on_mount(self) -> None:
        """Set initial progress."""
        self._update_bar()

    def update_hp(self, current: int, maximum: int | None = None) -> None:
        """Update the HP display."""
        self.current = current
        if maximum is not None:
            self.maximum = maximum
        self._update_bar()

    def _update_bar(self) -> None:
        """Update the progress bar."""
        label = self.query_one("#hp-label", Label)
        label.update(f"HP: {self.current}/{self.maximum}")

        bar = self.query_one("#hp-bar", ProgressBar)
        bar.total = self.maximum
        bar.progress = self.current

        # Change color based on HP percentage
        pct = (self.current / self.maximum) * 100 if self.maximum else 0
        if pct > 50:
            bar.styles.color = "green"
        elif pct > 25:
            bar.styles.color = "yellow"
        else:
            bar.styles.color = "red"


class AbilityScoreWidget(Static):
    """Display ability scores in a compact format."""

    CSS = """
    AbilityScoreWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    .ability-header {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }

    .ability-grid {
        height: auto;
    }

    .ability-row {
        height: 1;
    }

    .ability-name {
        width: 5;
        text-style: bold;
    }

    .ability-score {
        width: 4;
        text-align: right;
    }

    .ability-mod {
        width: 5;
        text-align: center;
        color: $accent;
    }
    """

    def __init__(self, abilities: dict[str, int] | None = None, **kwargs):
        """Initialize the ability score widget."""
        super().__init__(**kwargs)
        self.abilities = abilities or {
            "STR": 10, "DEX": 10, "CON": 10,
            "INT": 10, "WIS": 10, "CHA": 10,
        }

    def compose(self) -> ComposeResult:
        """Compose the ability score widget."""
        yield Label("Abilities", classes="ability-header")
        with Vertical(classes="ability-grid"):
            for ability, score in self.abilities.items():
                mod = (score - 10) // 2
                with Horizontal(classes="ability-row"):
                    yield Label(ability, classes="ability-name")
                    yield Label(str(score), classes="ability-score")
                    yield Label(f"({mod:+d})", classes="ability-mod")

    def update_abilities(self, abilities: dict[str, int]) -> None:
        """Update ability scores."""
        self.abilities = abilities
        self.refresh()


class CharacterDisplayWidget(Static):
    """A compact character sheet display widget."""

    CSS = """
    CharacterDisplayWidget {
        height: auto;
        border: solid $secondary;
        padding: 1;
    }

    .char-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .char-subtitle {
        color: $text-muted;
        margin-bottom: 1;
    }

    .stat-row {
        height: 1;
    }

    .stat-label {
        width: 8;
    }

    .stat-value {
        text-style: bold;
    }

    .section-divider {
        margin: 1 0;
        border-bottom: solid $primary-darken-2;
    }
    """

    def __init__(self, character: CharacterSheet | None = None, **kwargs):
        """Initialize the character display."""
        super().__init__(**kwargs)
        self.character = character

    def compose(self) -> ComposeResult:
        """Compose the character display."""
        if not self.character:
            yield Label("No character loaded", classes="char-header")
            return

        char = self.character

        # Name and basic info
        yield Label(char.name, classes="char-header")
        yield Label(
            f"{char.race} {char.character_class} {char.level}",
            classes="char-subtitle",
        )

        # HP bar
        yield HPBar(
            current=char.hit_points.current,
            maximum=char.hit_points.maximum,
            id="char-hp",
        )

        yield Static("", classes="section-divider")

        # Combat stats
        with Horizontal(classes="stat-row"):
            yield Label("AC:", classes="stat-label")
            yield Label(str(char.combat_stats.ac), classes="stat-value")

        with Horizontal(classes="stat-row"):
            yield Label("BAB:", classes="stat-label")
            yield Label(f"+{char.combat_stats.bab}", classes="stat-value")

        with Horizontal(classes="stat-row"):
            yield Label("CMB/CMD:", classes="stat-label")
            yield Label(
                f"+{char.combat_stats.cmb}/{char.combat_stats.cmd}",
                classes="stat-value",
            )

        yield Static("", classes="section-divider")

        # Saves
        with Horizontal(classes="stat-row"):
            yield Label("Fort:", classes="stat-label")
            yield Label(f"+{char.saving_throws.fortitude}", classes="stat-value")

        with Horizontal(classes="stat-row"):
            yield Label("Ref:", classes="stat-label")
            yield Label(f"+{char.saving_throws.reflex}", classes="stat-value")

        with Horizontal(classes="stat-row"):
            yield Label("Will:", classes="stat-label")
            yield Label(f"+{char.saving_throws.will}", classes="stat-value")

        yield Static("", classes="section-divider")

        # Ability scores
        yield AbilityScoreWidget(
            abilities={
                "STR": char.ability_scores.strength,
                "DEX": char.ability_scores.dexterity,
                "CON": char.ability_scores.constitution,
                "INT": char.ability_scores.intelligence,
                "WIS": char.ability_scores.wisdom,
                "CHA": char.ability_scores.charisma,
            },
        )

    def update_character(self, character: CharacterSheet) -> None:
        """Update the displayed character."""
        self.character = character
        self.refresh()
