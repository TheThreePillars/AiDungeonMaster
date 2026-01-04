"""Dice roller widget for AI Dungeon Master."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Static

from ...game.dice import DiceRoller, DiceResult


class DiceRollerWidget(Static):
    """A widget for rolling dice with various options."""

    CSS = """
    DiceRollerWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    .roller-header {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }

    .dice-buttons {
        height: 3;
        margin-bottom: 1;
    }

    .dice-buttons Button {
        min-width: 6;
        margin-right: 1;
    }

    #dice-input-row {
        height: 3;
        margin-bottom: 1;
    }

    #dice-input {
        width: 1fr;
    }

    #roll-button {
        width: 10;
    }

    #dice-result-display {
        height: auto;
        min-height: 3;
        border: solid $success;
        padding: 1;
        text-align: center;
    }

    .result-total {
        text-style: bold;
        color: $success;
    }

    .result-detail {
        color: $text-muted;
    }

    .result-crit {
        color: $success;
        text-style: bold;
    }

    .result-fumble {
        color: $error;
        text-style: bold;
    }
    """

    class DiceRolled(Message):
        """Message sent when dice are rolled."""

        def __init__(self, result: DiceResult) -> None:
            """Initialize the message."""
            self.result = result
            super().__init__()

    def __init__(self, **kwargs):
        """Initialize the dice roller widget."""
        super().__init__(**kwargs)
        self.roller = DiceRoller()
        self.last_result: DiceResult | None = None

    def compose(self) -> ComposeResult:
        """Compose the dice roller widget."""
        yield Label("Dice Roller", classes="roller-header")

        # Quick dice buttons
        with Horizontal(classes="dice-buttons"):
            yield Button("d4", id="btn-d4")
            yield Button("d6", id="btn-d6")
            yield Button("d8", id="btn-d8")
            yield Button("d10", id="btn-d10")
            yield Button("d12", id="btn-d12")
            yield Button("d20", id="btn-d20")

        # Custom dice input
        with Horizontal(id="dice-input-row"):
            yield Input(placeholder="e.g., 2d6+3", id="dice-input")
            yield Button("Roll", id="roll-button", variant="primary")

        # Result display
        yield Static("Roll some dice!", id="dice-result-display")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        dice_map = {
            "btn-d4": "1d4",
            "btn-d6": "1d6",
            "btn-d8": "1d8",
            "btn-d10": "1d10",
            "btn-d12": "1d12",
            "btn-d20": "1d20",
        }

        if button_id in dice_map:
            self._roll(dice_map[button_id])
        elif button_id == "roll-button":
            input_widget = self.query_one("#dice-input", Input)
            if input_widget.value:
                self._roll(input_widget.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "dice-input" and event.value:
            self._roll(event.value)

    def _roll(self, notation: str) -> None:
        """Roll dice with the given notation."""
        try:
            result = self.roller.roll(notation)
            self.last_result = result
            self._display_result(notation, result)
            self.post_message(self.DiceRolled(result))
        except ValueError as e:
            display = self.query_one("#dice-result-display", Static)
            display.update(f"[red]Invalid notation: {e}[/red]")

    def _display_result(self, notation: str, result: DiceResult) -> None:
        """Display the roll result."""
        display = self.query_one("#dice-result-display", Static)

        # Build result text
        text = f"[bold]{notation}[/bold]\n"
        text += f"[bold green]{result.total}[/bold green]\n"
        text += f"[dim]Rolls: {result.rolls}[/dim]"

        # Add special indicators
        if result.is_critical:
            text += "\n[bold green]CRITICAL![/bold green]"
        elif result.is_fumble:
            text += "\n[bold red]FUMBLE![/bold red]"

        display.update(text)

    def roll(self, notation: str) -> DiceResult:
        """Roll dice programmatically."""
        self._roll(notation)
        return self.last_result
