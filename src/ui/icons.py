"""Modern Unicode emoji icons for the UI.

Uses standard Unicode emoji that work on Windows terminals.
"""


class Icons:
    """Icon set using Unicode emoji for modern appearance."""

    # Navigation
    BACK = "◀"
    FORWARD = "▶"
    UP = "▲"
    DOWN = "▼"
    MENU = "☰"
    CLOSE = "✕"
    CHECK = "✓"
    CANCEL = "✕"

    # Game Actions
    PLAY = "▶"
    NEW = "✚"
    SAVE = "💾"
    LOAD = "📂"
    SETTINGS = "⚙"
    QUIT = "⏻"

    # Character & Party
    CHARACTER = "👤"
    PARTY = "👥"
    LEVEL_UP = "⬆"
    EDIT = "✎"
    DELETE = "🗑"

    # Combat
    SWORD = "⚔"
    SHIELD = "🛡"
    HEART = "❤"
    SKULL = "💀"
    DICE = "🎲"
    TARGET = "◎"

    # Magic & Items
    MAGIC = "✨"
    POTION = "🧪"
    SCROLL = "📜"
    BOOK = "📖"
    CHEST = "📦"
    GOLD = "💰"

    # Exploration
    MAP = "🗺"
    COMPASS = "🧭"
    LOCATION = "📍"
    TRAVEL = "🚶"
    HOUSE = "🏠"
    CASTLE = "🏰"

    # NPCs & Quests
    NPC = "💬"
    QUEST = "📋"
    CHAT = "💭"
    TRADE = "🔄"

    # Status
    INFO = "ℹ"
    WARNING = "⚠"
    ERROR = "❌"
    SUCCESS = "✅"
    HELP = "❓"
    TIME = "🕐"

    # Monsters
    MONSTER = "👹"
    DRAGON = "🐉"
    UNDEAD = "💀"

    # Misc
    STAR = "⭐"
    FIRE = "🔥"
    REST = "😴"


# Fallback to simple ASCII if needed
class SimpleIcons:
    """Simple ASCII icons for maximum compatibility."""

    BACK = "<"
    FORWARD = ">"
    UP = "^"
    DOWN = "v"
    MENU = "="
    CLOSE = "x"
    CHECK = "+"
    CANCEL = "x"

    PLAY = ">"
    NEW = "+"
    SAVE = "S"
    LOAD = "L"
    SETTINGS = "*"
    QUIT = "Q"

    CHARACTER = "C"
    PARTY = "P"
    LEVEL_UP = "^"
    EDIT = "E"
    DELETE = "D"

    SWORD = "/"
    SHIELD = "O"
    HEART = "<3"
    SKULL = "X"
    DICE = "d"
    TARGET = "o"

    MAGIC = "*"
    POTION = "!"
    SCROLL = "~"
    BOOK = "#"
    CHEST = "="
    GOLD = "$"

    MAP = "M"
    COMPASS = "@"
    LOCATION = "*"
    TRAVEL = ">"
    HOUSE = "H"
    CASTLE = "C"

    NPC = "?"
    QUEST = "!"
    CHAT = "."
    TRADE = "<>"

    INFO = "i"
    WARNING = "!"
    ERROR = "X"
    SUCCESS = "+"
    HELP = "?"
    TIME = "@"

    MONSTER = "M"
    DRAGON = "D"
    UNDEAD = "U"

    STAR = "*"
    FIRE = "~"
    REST = "z"
