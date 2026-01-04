"""Map view screen for location navigation."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, Static


# Define locations and connections for Sandpoint area
LOCATIONS = {
    "rusty_dragon": {
        "name": "The Rusty Dragon Inn",
        "description": "A warm and inviting tavern in the heart of Sandpoint.",
        "connections": ["town_square", "waterfront"],
        "npcs": ["Ameiko Kaijitsu", "Bethana Corwin"],
        "map_pos": (10, 5),
    },
    "town_square": {
        "name": "Sandpoint Town Square",
        "description": "The central plaza of Sandpoint, bustling with activity.",
        "connections": ["rusty_dragon", "cathedral", "market", "garrison"],
        "npcs": ["Mayor Deverin"],
        "map_pos": (10, 3),
    },
    "cathedral": {
        "name": "Sandpoint Cathedral",
        "description": "A beautiful stone cathedral dedicated to multiple deities.",
        "connections": ["town_square", "graveyard"],
        "npcs": ["Father Zantus"],
        "map_pos": (5, 2),
    },
    "market": {
        "name": "Sandpoint Market",
        "description": "Various stalls selling goods and provisions.",
        "connections": ["town_square", "general_store"],
        "npcs": ["Various merchants"],
        "map_pos": (15, 2),
    },
    "garrison": {
        "name": "Sandpoint Garrison",
        "description": "The town guard headquarters and jail.",
        "connections": ["town_square"],
        "npcs": ["Sheriff Hemlock"],
        "map_pos": (15, 4),
    },
    "waterfront": {
        "name": "Sandpoint Waterfront",
        "description": "The docks and harbor of Sandpoint.",
        "connections": ["rusty_dragon", "fish_market"],
        "npcs": ["Fishermen"],
        "map_pos": (10, 7),
    },
    "graveyard": {
        "name": "Sandpoint Boneyard",
        "description": "The town's graveyard, quiet and eerie.",
        "connections": ["cathedral"],
        "npcs": [],
        "map_pos": (2, 3),
    },
    "general_store": {
        "name": "Sandpoint General Store",
        "description": "Ven Vinder's well-stocked general store.",
        "connections": ["market"],
        "npcs": ["Ven Vinder", "Shayliss Vinder"],
        "map_pos": (18, 1),
    },
    "fish_market": {
        "name": "Fish Market",
        "description": "Fresh catch from the harbor, sold daily.",
        "connections": ["waterfront"],
        "npcs": ["Fishmongers"],
        "map_pos": (7, 8),
    },
}

# Map location IDs to short display names
LOCATION_MAP = {
    "The Rusty Dragon Inn": "rusty_dragon",
    "Sandpoint Town Square": "town_square",
    "Sandpoint Cathedral": "cathedral",
    "Sandpoint Market": "market",
    "Sandpoint Garrison": "garrison",
    "Sandpoint Waterfront": "waterfront",
    "Sandpoint Boneyard": "graveyard",
    "Sandpoint General Store": "general_store",
    "Fish Market": "fish_market",
}


class MapViewScreen(Screen):
    """Screen for viewing the world map."""

    CSS = """
    MapViewScreen {
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }

    #map-panel {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    #info-panel {
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #ascii-map {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #location-list {
        height: auto;
        max-height: 15;
        margin-bottom: 1;
    }

    #location-info {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #button-row {
        dock: bottom;
        height: 3;
    }

    Button {
        margin-right: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.current_location_id = "rusty_dragon"
        self.visited_locations = {"rusty_dragon"}

    def compose(self) -> ComposeResult:
        with Container(id="map-panel"):
            yield Label("World Map - Sandpoint", classes="section-header")
            yield Static(self._render_map(), id="ascii-map")

            with Horizontal(id="button-row"):
                yield Button("Travel", id="btn-travel", variant="primary")
                yield Button("Back", id="btn-back")

        with Container(id="info-panel"):
            yield Label("Locations", classes="section-header")
            yield DataTable(id="location-list")
            yield Label("Location Details", classes="section-header")
            yield Static("Select a location for details.", id="location-info")

    def on_mount(self) -> None:
        """Set up the screen."""
        # Get current location from game state
        game_state = self.app.game_state
        current_name = game_state.current_location
        self.current_location_id = LOCATION_MAP.get(current_name, "rusty_dragon")
        self.visited_locations.add(self.current_location_id)

        # Set up location table
        table = self.query_one("#location-list", DataTable)
        table.add_columns("Location", "Status")
        table.cursor_type = "row"

        self._populate_location_table()
        self._update_map()
        self._show_current_location()

    def _populate_location_table(self) -> None:
        """Populate the location table."""
        table = self.query_one("#location-list", DataTable)
        table.clear()

        for loc_id, loc_data in LOCATIONS.items():
            if loc_id in self.visited_locations:
                status = "(+) Visited" if loc_id != self.current_location_id else "(*) Here"
            elif self._is_adjacent(loc_id):
                status = "-> Adjacent"
            else:
                status = "? Unknown"

            table.add_row(loc_data["name"], status, key=loc_id)

    def _is_adjacent(self, loc_id: str) -> bool:
        """Check if a location is adjacent to current location."""
        current = LOCATIONS.get(self.current_location_id, {})
        return loc_id in current.get("connections", [])

    def _render_map(self) -> str:
        """Render the ASCII map."""
        # Create a simple ASCII map
        width = 25
        height = 10
        grid = [[" " for _ in range(width)] for _ in range(height)]

        # Draw locations
        for loc_id, loc_data in LOCATIONS.items():
            x, y = loc_data["map_pos"]
            if x < width and y < height:
                if loc_id == self.current_location_id:
                    char = "*"
                elif loc_id in self.visited_locations:
                    char = "@"
                elif self._is_adjacent(loc_id):
                    char = "o"
                else:
                    char = "."
                grid[y][x] = char

        # Draw connections (simplified)
        for loc_id, loc_data in LOCATIONS.items():
            if loc_id not in self.visited_locations and not self._is_adjacent(loc_id):
                continue

            x1, y1 = loc_data["map_pos"]
            for conn_id in loc_data["connections"]:
                if conn_id not in LOCATIONS:
                    continue
                if conn_id not in self.visited_locations and not self._is_adjacent(conn_id):
                    continue

                x2, y2 = LOCATIONS[conn_id]["map_pos"]

                # Draw horizontal line
                if y1 == y2:
                    for x in range(min(x1, x2) + 1, max(x1, x2)):
                        if grid[y1][x] == " ":
                            grid[y1][x] = "-"

                # Draw vertical line
                elif x1 == x2:
                    for y in range(min(y1, y2) + 1, max(y1, y2)):
                        if grid[y][x1] == " ":
                            grid[y][x1] = "|"

        # Build map string
        border = "+" + "-" * width + "+\n"
        result = border

        for row in grid:
            result += "|" + "".join(row) + "|\n"

        result += "+" + "-" * width + "+\n\n"
        result += "[bold]Legend:[/bold]\n"
        result += "* = Current  @ = Visited  o = Adjacent  . = Unknown"

        return result

    def _update_map(self) -> None:
        """Update the map display."""
        map_display = self.query_one("#ascii-map", Static)
        map_display.update(self._render_map())

    def _show_current_location(self) -> None:
        """Show details for current location."""
        loc_data = LOCATIONS.get(self.current_location_id, {})
        self._show_location_details(loc_data)

    def _show_location_details(self, loc_data: dict) -> None:
        """Show details for a location."""
        info = self.query_one("#location-info", Static)

        if not loc_data:
            info.update("Unknown location.")
            return

        text = f"[bold]{loc_data.get('name', 'Unknown')}[/bold]\n\n"
        text += f"{loc_data.get('description', 'No description.')}\n\n"

        npcs = loc_data.get("npcs", [])
        if npcs:
            text += "[bold]NPCs:[/bold]\n"
            for npc in npcs:
                text += f"  - {npc}\n"

        connections = loc_data.get("connections", [])
        if connections:
            text += "\n[bold]Connections:[/bold]\n"
            for conn_id in connections:
                conn_data = LOCATIONS.get(conn_id, {})
                conn_name = conn_data.get("name", conn_id)
                text += f"  -> {conn_name}\n"

        info.update(text)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle location selection."""
        loc_id = event.row_key.value if event.row_key else None
        if loc_id and loc_id in LOCATIONS:
            self._show_location_details(LOCATIONS[loc_id])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-back":
            self.app.pop_screen()
        elif button_id == "btn-travel":
            self._travel()

    def _travel(self) -> None:
        """Travel to selected location."""
        table = self.query_one("#location-list", DataTable)

        if table.cursor_row is None:
            self.app.notify("Select a location first.", title="Travel")
            return

        row_key = table.get_row_at(table.cursor_row)
        # Get location id from the data
        loc_id = None
        for key in self._get_table_keys():
            if key == str(table.cursor_row):
                loc_id = key
                break

        # Find selected location from cursor
        cursor_row = table.cursor_row
        loc_ids = list(LOCATIONS.keys())
        if cursor_row < len(loc_ids):
            loc_id = loc_ids[cursor_row]

        if not loc_id or loc_id not in LOCATIONS:
            self.app.notify("Invalid location.", title="Travel")
            return

        # Check if adjacent
        if not self._is_adjacent(loc_id) and loc_id != self.current_location_id:
            self.app.notify("You can only travel to adjacent locations.", title="Travel")
            return

        if loc_id == self.current_location_id:
            self.app.notify("You're already here!", title="Travel")
            return

        # Travel!
        self.current_location_id = loc_id
        self.visited_locations.add(loc_id)

        loc_data = LOCATIONS[loc_id]
        location_name = loc_data["name"]
        location_desc = loc_data["description"]

        # Update game state
        self.app.game_state.current_location = location_name
        self.app.game_state.location_description = location_desc

        self.app.notify(f"Traveled to {location_name}!", title="Travel")

        # Refresh display
        self._populate_location_table()
        self._update_map()
        self._show_current_location()

    def _get_table_keys(self) -> list[str]:
        """Get all table row keys."""
        return list(LOCATIONS.keys())
