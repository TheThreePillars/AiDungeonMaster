# AI Dungeon Master

An AI-powered Game Master for Pathfinder 1st Edition tabletop RPG, running locally with Ollama.

## Features

- **AI-Guided Character Creation**: Interactive character creation wizard powered by LLM
- **Full Pathfinder 1e Support**: Complete rules engine with skills, saves, combat, and conditions
- **Multiplayer Ready**: Party system supporting multiple player characters
- **Combat Tracker**: Initiative management, HP tracking, and condition management
- **Campaign Management**: Session tracking, NPC management, and quest logs
- **Terminal UI**: Clean Textual-based interface (work in progress)

## Requirements

- Python 3.11+
- Ollama with Hermes 3B or 7B model
- SQLite (included with Python)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-dungeon-master
```

2. Install dependencies:
```bash
pip install -e .
```

3. Ensure Ollama is running with the Hermes model:
```bash
ollama pull hermes3:latest
ollama serve
```

4. Run the application:
```bash
python -m src.main
```

## Project Structure

```
ai-dungeon-master/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── llm/                 # LLM integration
│   │   ├── client.py        # Ollama client wrapper
│   │   ├── memory.py        # Conversation memory
│   │   └── prompts.py       # System prompts
│   ├── game/                # Game mechanics
│   │   ├── dice.py          # Dice rolling engine
│   │   ├── rules.py         # PF1e rules engine
│   │   ├── combat.py        # Combat tracker
│   │   └── conditions.py    # Status effects
│   ├── characters/          # Character system
│   │   ├── sheet.py         # Character sheet model
│   │   ├── creator.py       # Character creation
│   │   ├── inventory.py     # Equipment management
│   │   ├── races.py         # Race definitions
│   │   └── classes.py       # Class definitions
│   ├── campaign/            # Campaign management
│   │   ├── generator.py     # Campaign generation
│   │   ├── world.py         # World state
│   │   ├── npcs.py          # NPC management
│   │   └── quests.py        # Quest tracking
│   ├── database/            # Persistence
│   │   ├── models.py        # SQLAlchemy models
│   │   └── session.py       # DB session management
│   └── ui/                  # Terminal UI (Textual)
│       ├── app.py           # Main app
│       ├── screens/         # UI screens
│       └── widgets/         # Custom widgets
├── data/
│   ├── srd/                 # Pathfinder SRD data
│   │   ├── classes.json
│   │   ├── races.json
│   │   ├── spells.json
│   │   ├── equipment.json
│   │   └── monsters.json
│   └── prompts/             # LLM prompt templates
├── saves/                   # Save files
├── tests/                   # Test suite
├── config.yaml              # User configuration
└── pyproject.toml           # Project dependencies
```

## Configuration

Edit `config.yaml` to customize:

```yaml
llm:
  model: hermes3:latest     # Or hermes3:7b for better responses
  temperature: 0.8
  max_tokens: 1024

game:
  ruleset: pf1e
  difficulty: normal
  narration_style: detailed
  max_party_size: 6

combat:
  initiative_style: individual
  confirm_criticals: true    # PF1e critical confirmation
```

## Dice Notation

The dice engine supports full PF1e notation:

```python
from src.game.dice import roll

roll("1d20+5")              # Standard roll with modifier
roll("2d6+4")               # Multiple dice
roll("1d20 advantage")      # Roll twice, take higher
roll("4d6 drop lowest")     # Ability score rolling
roll("1d20 disadvantage")   # Roll twice, take lower
```

## Running Tests

```bash
pytest tests/ -v
```

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run linting:
```bash
ruff check src/
black src/
mypy src/
```

## License

MIT License

## Acknowledgments

- Pathfinder is a trademark of Paizo Inc.
- This project uses the Pathfinder Roleplaying Game Reference Document (PRD) under the Open Game License.
