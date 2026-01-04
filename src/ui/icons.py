"""Material Design inspired icons for the UI.

Uses Unicode symbols that render well in terminals.
"""

# Navigation & Actions
ICON_BACK = "󰁍"  # arrow left
ICON_FORWARD = "󰁔"  # arrow right
ICON_UP = "󰁛"  # arrow up
ICON_DOWN = "󰁅"  # arrow down
ICON_MENU = "󰍜"  # menu
ICON_CLOSE = "󰅖"  # close
ICON_CHECK = "󰄬"  # check
ICON_CANCEL = "󰅙"  # cancel

# Game Actions
ICON_PLAY = "󰐊"  # play
ICON_NEW = "󰐕"  # plus
ICON_SAVE = "󰆓"  # save/floppy
ICON_LOAD = "󰷊"  # folder open
ICON_SETTINGS = "󰒓"  # cog/gear
ICON_QUIT = "󰗼"  # exit

# Character & Party
ICON_CHARACTER = "󰀄"  # account
ICON_PARTY = "󰡉"  # account group
ICON_LEVEL_UP = "󰁞"  # arrow up bold
ICON_EDIT = "󰏫"  # pencil
ICON_DELETE = "󰆴"  # trash

# Combat
ICON_SWORD = "󰓥"  # sword
ICON_SHIELD = "󰒡"  # shield
ICON_HEART = "󰋑"  # heart
ICON_SKULL = "󰊱"  # skull
ICON_DICE = "󰡛"  # dice d20
ICON_TARGET = "󰓾"  # target

# Magic & Items
ICON_MAGIC = "󰂖"  # auto-fix / magic wand
ICON_POTION = "󰂓"  # flask
ICON_SCROLL = "󰈙"  # file document
ICON_BOOK = "󰂽"  # book open
ICON_CHEST = "󱊴"  # treasure chest
ICON_GOLD = "󰆧"  # currency

# Exploration
ICON_MAP = "󰍐"  # map
ICON_COMPASS = "󰇂"  # compass
ICON_LOCATION = "󰍎"  # map marker
ICON_TRAVEL = "󰠁"  # walk
ICON_HOUSE = "󰋜"  # home
ICON_CASTLE = "󱃲"  # castle

# NPCs & Quests
ICON_NPC = "󰓃"  # account voice
ICON_QUEST = "󰃤"  # flag
ICON_CHAT = "󰍡"  # message
ICON_TRADE = "󰤏"  # swap horizontal

# Status & Info
ICON_INFO = "󰋽"  # information
ICON_WARNING = "󰀦"  # alert
ICON_ERROR = "󰅚"  # alert circle
ICON_SUCCESS = "󰄭"  # check circle
ICON_HELP = "󰋗"  # help circle
ICON_TIME = "󰥔"  # clock

# Monsters
ICON_MONSTER = "󰚌"  # ghost (bestiary)
ICON_DRAGON = "󱍼"  # dragon
ICON_UNDEAD = "󰊱"  # skull

# Misc
ICON_STAR = "󰓎"  # star
ICON_FIRE = "󰈸"  # fire
ICON_REST = "󰒲"  # sleep/moon


# Fallback ASCII icons for terminals without Nerd Font support
class Icons:
    """Icon set with fallback support."""

    # Try to detect if terminal supports special characters
    # For now, use simple Unicode that works everywhere

    # Navigation
    BACK = "◀"
    FORWARD = "▶"
    UP = "▲"
    DOWN = "▼"
    MENU = "☰"
    CLOSE = "✕"
    CHECK = "✓"
    CANCEL = "✗"

    # Game Actions
    PLAY = "▶"
    NEW = "+"
    SAVE = "💾"
    LOAD = "📂"
    SETTINGS = "⚙"
    QUIT = "⏻"

    # Character & Party
    CHARACTER = "👤"
    PARTY = "👥"
    LEVEL_UP = "⬆"
    EDIT = "✏"
    DELETE = "🗑"

    # Combat
    SWORD = "⚔"
    SHIELD = "🛡"
    HEART = "♥"
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
    QUEST = "🚩"
    CHAT = "💭"
    TRADE = "🔄"

    # Status
    INFO = "ℹ"
    WARNING = "⚠"
    ERROR = "⛔"
    SUCCESS = "✅"
    HELP = "❓"
    TIME = "🕐"

    # Monsters
    MONSTER = "👹"
    DRAGON = "🐉"
    UNDEAD = "💀"

    # Misc
    STAR = "★"
    FIRE = "🔥"
    REST = "🌙"


# Simple ASCII fallback for maximum compatibility
class SimpleIcons:
    """Simple ASCII icons for maximum terminal compatibility."""

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
    SAVE = "[S]"
    LOAD = "[L]"
    SETTINGS = "[*]"
    QUIT = "[Q]"

    CHARACTER = "[C]"
    PARTY = "[P]"
    LEVEL_UP = "^"
    EDIT = "[E]"
    DELETE = "[D]"

    SWORD = "/"
    SHIELD = "O"
    HEART = "<3"
    SKULL = "X"
    DICE = "[d]"
    TARGET = "()"

    MAGIC = "*"
    POTION = "!"
    SCROLL = "~"
    BOOK = "#"
    CHEST = "[]"
    GOLD = "$"

    MAP = "[M]"
    COMPASS = "@"
    LOCATION = "*"
    TRAVEL = ">"
    HOUSE = "^"
    CASTLE = "#"

    NPC = "?"
    QUEST = "!"
    CHAT = "..."
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


# Default icon set - use Unicode emoji icons
icons = Icons()
