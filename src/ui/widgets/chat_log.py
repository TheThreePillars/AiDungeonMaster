"""Chat log widget for AI Dungeon Master."""

from datetime import datetime
from enum import Enum
from typing import NamedTuple

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, RichLog, Static


class MessageType(Enum):
    """Type of chat message."""

    PLAYER = "player"
    DM = "dm"
    SYSTEM = "system"
    DICE = "dice"
    COMBAT = "combat"


class ChatMessage(NamedTuple):
    """A chat message."""

    content: str
    message_type: MessageType
    timestamp: datetime = None

    @property
    def formatted(self) -> str:
        """Get formatted message for display."""
        time_str = ""
        if self.timestamp:
            time_str = f"[dim]{self.timestamp.strftime('%H:%M')}[/dim] "

        type_styles = {
            MessageType.PLAYER: ("[bold cyan]> [/bold cyan]", ""),
            MessageType.DM: ("[bold magenta]DM: [/bold magenta]", ""),
            MessageType.SYSTEM: ("[dim italic]", "[/dim italic]"),
            MessageType.DICE: ("[bold yellow]", "[/bold yellow]"),
            MessageType.COMBAT: ("[bold red]", "[/bold red]"),
        }

        prefix, suffix = type_styles.get(self.message_type, ("", ""))
        return f"{time_str}{prefix}{self.content}{suffix}"


class ChatLogWidget(Static):
    """A chat log widget for game narrative and player input."""

    CSS = """
    ChatLogWidget {
        height: 100%;
        border: solid $secondary;
    }

    #chat-log {
        height: 1fr;
        border: none;
        padding: 1;
    }

    #chat-input-container {
        dock: bottom;
        height: 3;
        padding: 0 1;
        border-top: solid $primary;
    }

    #chat-input {
        width: 100%;
    }
    """

    class PlayerMessage(Message):
        """Message sent when player submits input."""

        def __init__(self, content: str) -> None:
            """Initialize the message."""
            self.content = content
            super().__init__()

    def __init__(self, show_input: bool = True, **kwargs):
        """Initialize the chat log.

        Args:
            show_input: Whether to show the input field
            **kwargs: Additional arguments
        """
        super().__init__(**kwargs)
        self.show_input = show_input
        self.messages: list[ChatMessage] = []

    def compose(self) -> ComposeResult:
        """Compose the chat log widget."""
        yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)

        if self.show_input:
            with Vertical(id="chat-input-container"):
                yield Input(
                    placeholder="What do you do? (type /help for commands)",
                    id="chat-input",
                )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "chat-input" and event.value.strip():
            content = event.value.strip()
            event.input.clear()

            # Add player message to log
            self.add_message(content, MessageType.PLAYER)

            # Notify parent
            self.post_message(self.PlayerMessage(content))

    def add_message(
        self,
        content: str,
        message_type: MessageType = MessageType.DM,
        show_timestamp: bool = False,
    ) -> None:
        """Add a message to the chat log.

        Args:
            content: Message content
            message_type: Type of message
            show_timestamp: Whether to show timestamp
        """
        timestamp = datetime.now() if show_timestamp else None
        message = ChatMessage(content, message_type, timestamp)
        self.messages.append(message)

        log = self.query_one("#chat-log", RichLog)
        log.write(message.formatted)

    def add_player_message(self, content: str) -> None:
        """Add a player message."""
        self.add_message(content, MessageType.PLAYER)

    def add_dm_message(self, content: str) -> None:
        """Add a DM/AI message."""
        self.add_message(content, MessageType.DM)

    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        self.add_message(content, MessageType.SYSTEM)

    def add_dice_message(self, content: str) -> None:
        """Add a dice roll message."""
        self.add_message(content, MessageType.DICE)

    def add_combat_message(self, content: str) -> None:
        """Add a combat message."""
        self.add_message(content, MessageType.COMBAT)

    def clear(self) -> None:
        """Clear the chat log."""
        self.messages.clear()
        log = self.query_one("#chat-log", RichLog)
        log.clear()

    def write_streaming(self, token: str) -> None:
        """Write a streaming token (for AI responses).

        This appends to the current line without creating a new one.
        """
        log = self.query_one("#chat-log", RichLog)
        log.write(token, scroll_end=True)
