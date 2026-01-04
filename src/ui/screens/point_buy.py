"""Point buy screen for ability score generation."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


# Point costs for ability scores (Pathfinder standard)
POINT_COSTS = {
    7: -4, 8: -2, 9: -1, 10: 0, 11: 1, 12: 2, 13: 3,
    14: 5, 15: 7, 16: 10, 17: 13, 18: 17,
}


class PointBuyScreen(ModalScreen):
    """Modal screen for point buy ability score generation."""

    CSS = """
    PointBuyScreen {
        align: center middle;
    }

    #point-buy-dialog {
        width: 50;
        height: 25;
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

    .ability-row {
        height: 3;
        margin-bottom: 0;
    }

    .ability-label {
        width: 6;
        text-style: bold;
    }

    .ability-score {
        width: 4;
        text-align: center;
    }

    .ability-mod {
        width: 5;
        color: $text-muted;
    }

    .ability-cost {
        width: 8;
        color: $warning;
    }

    #points-remaining {
        text-align: center;
        text-style: bold;
        border: solid $accent;
        padding: 1;
        margin: 1 0;
    }

    #button-row {
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, total_points: int = 20):
        super().__init__()
        self.total_points = total_points
        self.scores = {
            "STR": 10, "DEX": 10, "CON": 10,
            "INT": 10, "WIS": 10, "CHA": 10,
        }

    def compose(self) -> ComposeResult:
        with Container(id="point-buy-dialog"):
            yield Label(f"Point Buy ({self.total_points} points)", classes="header")

            for ability in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
                with Horizontal(classes="ability-row"):
                    yield Label(f"{ability}:", classes="ability-label")
                    yield Button("-", id=f"dec-{ability}", variant="error")
                    yield Static(str(self.scores[ability]), id=f"score-{ability}", classes="ability-score")
                    yield Button("+", id=f"inc-{ability}", variant="success")
                    yield Static(self._get_mod_str(self.scores[ability]), id=f"mod-{ability}", classes="ability-mod")
                    yield Static(f"Cost: {POINT_COSTS[self.scores[ability]]}", id=f"cost-{ability}", classes="ability-cost")

            yield Static(self._get_points_display(), id="points-remaining")

            with Horizontal(id="button-row"):
                yield Button("Accept", id="btn-accept", variant="primary")
                yield Button("Reset", id="btn-reset")
                yield Button("Cancel", id="btn-cancel")

    def _get_mod_str(self, score: int) -> str:
        """Get modifier string."""
        mod = (score - 10) // 2
        return f"({mod:+d})"

    def _get_total_cost(self) -> int:
        """Calculate total point cost."""
        return sum(POINT_COSTS[score] for score in self.scores.values())

    def _get_points_display(self) -> str:
        """Get points remaining display."""
        used = self._get_total_cost()
        remaining = self.total_points - used
        color = "green" if remaining >= 0 else "red"
        return f"[{color}]Points: {remaining} remaining ({used}/{self.total_points} used)[/{color}]"

    def _update_ability_display(self, ability: str) -> None:
        """Update display for one ability."""
        score = self.scores[ability]

        score_label = self.query_one(f"#score-{ability}", Static)
        score_label.update(str(score))

        mod_label = self.query_one(f"#mod-{ability}", Static)
        mod_label.update(self._get_mod_str(score))

        cost_label = self.query_one(f"#cost-{ability}", Static)
        cost_label.update(f"Cost: {POINT_COSTS[score]}")

        points_label = self.query_one("#points-remaining", Static)
        points_label.update(self._get_points_display())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id.startswith("inc-"):
            ability = button_id[4:]
            self._increase_ability(ability)
        elif button_id.startswith("dec-"):
            ability = button_id[4:]
            self._decrease_ability(ability)
        elif button_id == "btn-accept":
            if self._get_total_cost() <= self.total_points:
                self.dismiss(self.scores.copy())
            else:
                self.app.notify("Too many points spent!", title="Point Buy", severity="error")
        elif button_id == "btn-reset":
            self._reset_scores()
        elif button_id == "btn-cancel":
            self.dismiss(None)

    def _increase_ability(self, ability: str) -> None:
        """Increase an ability score."""
        current = self.scores[ability]
        if current < 18:
            new_score = current + 1
            new_cost = self._get_total_cost() - POINT_COSTS[current] + POINT_COSTS[new_score]
            if new_cost <= self.total_points:
                self.scores[ability] = new_score
                self._update_ability_display(ability)

    def _decrease_ability(self, ability: str) -> None:
        """Decrease an ability score."""
        current = self.scores[ability]
        if current > 7:
            self.scores[ability] = current - 1
            self._update_ability_display(ability)

    def _reset_scores(self) -> None:
        """Reset all scores to 10."""
        for ability in self.scores:
            self.scores[ability] = 10
            self._update_ability_display(ability)
