# AI Dungeon Master - Claude Code Project Prompt

## Project Overview

Create a Python-based AI Dungeon Master application that runs locally using Ollama with Hermes 3B (upgradeable to 7B). The system should handle character creation, campaign generation, combat tracking, dice rolling, and rules interpretation for D&D 5e.

## Technical Stack

- **Runtime:** Python 3.11+
- **LLM Backend:** Ollama (ollama-python library)
- **Database:** SQLite with SQLAlchemy ORM
- **UI:** Textual (terminal UI) for v1, with architecture supporting future web UI
- **Config:** YAML or TOML for settings
- **Testing:** pytest

## Project Structure

```
ai-dungeon-master/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration management
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # Ollama client wrapper
│   │   ├── prompts.py          # System prompts and templates
│   │   └── memory.py           # Conversation/context management
│   ├── game/
│   │   ├── __init__.py
│   │   ├── dice.py             # Dice rolling engine
│   │   ├── rules.py            # D&D 5e rules logic (hardcoded mechanics)
│   │   ├── combat.py           # Combat tracker and initiative
│   │   └── conditions.py       # Status effects and conditions
│   ├── characters/
│   │   ├── __init__.py
│   │   ├── creator.py          # Character creation wizard
│   │   ├── sheet.py            # Character sheet data model
│   │   ├── classes.py          # Class definitions and features
│   │   ├── races.py            # Race definitions and traits
│   │   └── inventory.py        # Equipment and item management
│   ├── campaign/
│   │   ├── __init__.py
│   │   ├── generator.py        # Campaign/adventure generation
│   │   ├── world.py            # World state and lore
│   │   ├── npcs.py             # NPC generation and tracking
│   │   └── quests.py           # Quest tracking
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── session.py          # DB session management
│   │   └── migrations/         # Alembic migrations (optional)
│   └── ui/
│       ├── __init__.py
│       ├── app.py              # Textual app main
│       ├── screens/            # UI screens
│       │   ├── main_menu.py
│       │   ├── character_creation.py
│       │   ├── game_session.py
│       │   └── combat_view.py
│       └── widgets/            # Custom widgets
│           ├── dice_roller.py
│           ├── character_display.py
│           └── chat_log.py
├── data/
│   ├── srd/                    # D&D 5e SRD reference data (JSON)
│   │   ├── classes.json
│   │   ├── races.json
│   │   ├── spells.json
│   │   ├── equipment.json
│   │   └── monsters.json
│   └── prompts/                # LLM prompt templates
│       ├── dm_system.txt
│       ├── character_interview.txt
│       ├── combat_narrator.txt
│       └── world_builder.txt
├── saves/                      # Save game directory
├── tests/
│   ├── test_dice.py
│   ├── test_combat.py
│   ├── test_character.py
│   └── test_llm_integration.py
├── config.yaml                 # User configuration
├── pyproject.toml              # Project dependencies
└── README.md
```

## Core Features to Implement

### Phase 1: Foundation
1. **Project scaffolding** - Set up the directory structure, pyproject.toml with dependencies, and basic config
2. **Dice engine** - Implement dice notation parser (e.g., "2d6+4", "1d20 advantage")
3. **Database models** - Character sheets, campaigns, sessions, NPCs
4. **Ollama client** - Wrapper with streaming support and conversation history

### Phase 2: Character System
1. **Character creation wizard** - AI-guided questionnaire that asks about:
   - Desired playstyle (combat, social, exploration, magic)
   - Character concept/fantasy
   - Background preferences
   - Then generates appropriate race/class suggestions
2. **Character sheet management** - Full 5e character sheet with:
   - Ability scores (point buy, standard array, or rolled)
   - Race and class features
   - Skills and proficiencies
   - HP, AC, and combat stats
   - Inventory and equipment
   - Spell slots and known spells (if applicable)
   - Experience and leveling

### Phase 3: Game Engine
1. **Combat tracker** - Initiative order, HP tracking, turn management
2. **Rules interpreter** - Skill checks, saving throws, attack rolls with modifiers
3. **Condition tracking** - Buffs, debuffs, concentration, death saves

### Phase 4: Campaign & Narrative
1. **Session memory** - Summarize and store session events
2. **World state** - Track locations, factions, NPC relationships
3. **Dynamic campaign generation** - Generate plot hooks, encounters, NPCs on the fly
4. **Quest tracker** - Active and completed quests with objectives

### Phase 5: UI
1. **Terminal UI with Textual** - Clean, navigable interface
2. **Chat/narrative panel** - Scrollable game log with DM narration
3. **Character sidebar** - Quick stats reference
4. **Dice roller widget** - Visual dice rolling with results
5. **Combat mode** - Initiative tracker, turn indicator, quick actions

## Database Schema (Core Models)

```python
# Key tables needed:

# Characters
- id, name, player_name, campaign_id
- race, class, subclass, level, experience
- strength, dexterity, constitution, intelligence, wisdom, charisma
- max_hp, current_hp, temp_hp, armor_class
- proficiency_bonus, speed
- background, alignment, personality_traits, ideals, bonds, flaws
- backstory (text, AI-generated or player-written)
- created_at, updated_at

# Campaigns
- id, name, description, setting
- world_state (JSON - locations, factions, events)
- current_session_id
- created_at, updated_at

# Sessions
- id, campaign_id, session_number
- summary (AI-generated recap)
- events (JSON array of significant events)
- npcs_introduced, locations_visited
- started_at, ended_at

# NPCs
- id, campaign_id, name, description
- disposition, faction, location
- stats (JSON - for combat-relevant NPCs)
- relationship_to_party
- notes

# Inventory Items
- id, character_id, name, description
- item_type, quantity, weight
- properties (JSON - damage, AC bonus, etc.)
- equipped (boolean)

# Quests
- id, campaign_id, name, description
- status (active, completed, failed, abandoned)
- objectives (JSON array)
- rewards
```

## LLM Prompt Templates Needed

### 1. DM System Prompt
```
You are an experienced Dungeon Master running a D&D 5e campaign. You create immersive, 
descriptive narratives while respecting game mechanics. You:
- Describe scenes vividly but concisely
- Voice NPCs with distinct personalities
- Present meaningful choices to players
- Balance challenge with fun
- Track context from the current session

Current campaign context will be provided. Current character sheet will be provided.
Respond to player actions appropriately, calling for rolls when needed using the format:
[ROLL: skill_check/saving_throw/attack type DC/target]
```

### 2. Character Interview Prompt
```
You are helping a player create their D&D 5e character through conversation. 
Ask questions one at a time to understand:
1. What fantasy archetype excites them (warrior, mage, rogue, healer, etc.)
2. Preferred combat style (melee, ranged, magic, support)
3. Social role (leader, loner, comic relief, mysterious stranger)
4. A brief character concept or inspiration

Based on their answers, suggest 2-3 race/class combinations that fit.
After they choose, help them develop personality traits, background, and backstory.
Keep questions conversational and engaging.
```

### 3. Combat Narrator Prompt
```
Narrate combat actions dramatically but briefly. You receive:
- The action taken (attack, spell, ability)
- The roll result and whether it hits
- Damage dealt (if applicable)
- Current HP of target

Describe the action in 1-3 sentences. Vary your descriptions. 
Make critical hits feel epic and misses feel consequential but not frustrating.
```

## Configuration Options (config.yaml)

```yaml
llm:
  provider: ollama
  model: hermes3:latest  # or hermes:7b, mistral:7b, etc.
  base_url: http://localhost:11434
  temperature: 0.8
  max_tokens: 1024
  
game:
  ruleset: 5e
  difficulty: normal  # easy, normal, hard (affects encounter balance)
  auto_roll: false    # DM rolls for players or players roll themselves
  narration_style: detailed  # brief, detailed, dramatic
  
ui:
  theme: dark
  dice_animation: true
  combat_log_length: 50
  
paths:
  saves: ./saves
  srd_data: ./data/srd
```

## Key Implementation Notes

### Dice Engine Requirements
- Parse standard notation: `NdX`, `NdX+M`, `NdX-M`
- Support advantage/disadvantage: `1d20 adv`, `1d20 dis`
- Support dropping dice: `4d6 drop lowest`
- Return structured result: `{rolls: [4, 6, 2], dropped: [2], modifier: 3, total: 13}`

### Memory/Context Management
- Keep last N messages in context for immediate conversation
- Generate session summaries periodically (every 10-15 exchanges or on demand)
- Store summaries in database for long-term campaign continuity
- Inject relevant context (character sheet, recent events, active quests) into system prompt

### Combat Flow
1. Trigger combat → Roll initiative for all participants
2. Display initiative order
3. On each turn: Present options → Player/AI chooses action → Resolve with rolls → Narrate result
4. Track HP, conditions, spell slots
5. Detect combat end (all enemies defeated, fled, or party TPK)
6. Award XP, generate loot if appropriate

### Error Handling
- Graceful fallback if Ollama is unavailable
- Save game state frequently (auto-save after significant events)
- Validate all dice notation before rolling
- Catch and handle LLM parsing errors

## Getting Started Commands

```bash
# Initialize the project
mkdir ai-dungeon-master && cd ai-dungeon-master
# (Claude Code will scaffold the structure)

# Install dependencies (after pyproject.toml is created)
pip install -e .

# Ensure Ollama is running with the model
ollama pull hermes3:latest
ollama serve

# Run the application
python -m src.main
```

## First Tasks for Claude Code

1. Create the project structure with all directories and `__init__.py` files
2. Create `pyproject.toml` with dependencies:
   - ollama
   - sqlalchemy
   - textual
   - pyyaml
   - pydantic (for data validation)
   - pytest (dev dependency)
3. Implement the dice engine (`src/game/dice.py`) with full notation support
4. Create database models (`src/database/models.py`)
5. Build the Ollama client wrapper (`src/llm/client.py`)
6. Create the character creation flow (`src/characters/creator.py`)

## Example Interaction Flow

```
┌────────────────────────────────────────────────────────────┐
│ AI DUNGEON MASTER                                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ DM: Welcome, adventurer! I'm excited to help you create   │
│     your character. First, tell me - what kind of hero    │
│     do you imagine yourself as? A mighty warrior? A       │
│     cunning rogue? A wielder of arcane power?             │
│                                                            │
│ > I want to play someone sneaky who uses magic            │
│                                                            │
│ DM: Ah, a blend of subtlety and sorcery! I love it.       │
│     Do you see yourself more as someone who uses magic    │
│     to enhance your stealth and trickery, or someone      │
│     who studied magic formally but prefers the shadows?   │
│                                                            │
│ [Character: None] [Session: New] [HP: --/--]              │
└────────────────────────────────────────────────────────────┘
```

---

## Notes

- Start with CLI/Textual UI; architecture should support adding a web UI later
- Keep LLM calls focused and specific; don't ask the model to do too much in one prompt
- Hardcode mechanical rules; use LLM for narrative and interpretation
- Test dice engine thoroughly - it's the foundation of everything
- Consider adding voice input/output later (you have ESP32 experience with this)
