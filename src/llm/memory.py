"""Conversation and context memory management for AI Dungeon Master."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .client import GenerationConfig, Message, OllamaClient


@dataclass
class ContextInfo:
    """Contextual information to inject into prompts."""

    # Party information (for multiplayer)
    party_summary: str | None = None
    active_character: str | None = None  # Name of character whose turn it is

    # Individual character summaries
    character_summaries: list[str] = field(default_factory=list)

    # World state
    current_location: str | None = None
    time_of_day: str | None = None
    weather: str | None = None

    # Active quests
    active_quests: list[str] = field(default_factory=list)

    # Recent events (short summaries)
    recent_events: list[str] = field(default_factory=list)

    # NPCs present
    npcs_present: list[str] = field(default_factory=list)

    # Combat state (if in combat)
    in_combat: bool = False
    combat_summary: str | None = None

    def to_context_string(self) -> str:
        """Convert context info to a string for injection into prompts."""
        parts = []

        if self.party_summary:
            parts.append(f"PARTY:\n{self.party_summary}")

        if self.character_summaries:
            parts.append("CHARACTERS:\n" + "\n".join(self.character_summaries))

        if self.current_location:
            location_info = f"LOCATION: {self.current_location}"
            if self.time_of_day:
                location_info += f" ({self.time_of_day})"
            if self.weather:
                location_info += f" - {self.weather}"
            parts.append(location_info)

        if self.active_quests:
            parts.append("ACTIVE QUESTS:\n- " + "\n- ".join(self.active_quests))

        if self.recent_events:
            parts.append("RECENT EVENTS:\n- " + "\n- ".join(self.recent_events[-5:]))

        if self.npcs_present:
            parts.append("NPCs PRESENT: " + ", ".join(self.npcs_present))

        if self.in_combat and self.combat_summary:
            parts.append(f"COMBAT STATUS:\n{self.combat_summary}")

        return "\n\n".join(parts)


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> Message:
        """Convert to a Message for the LLM."""
        return Message(role=self.role, content=self.content)


class ConversationMemory:
    """Manages conversation history and context for the game session."""

    def __init__(
        self,
        max_messages: int = 20,
        summary_threshold: int = 15,
        client: OllamaClient | None = None,
    ):
        """Initialize conversation memory.

        Args:
            max_messages: Maximum messages to keep in immediate context
            summary_threshold: Generate summary when this many messages accumulate
            client: OllamaClient for generating summaries (optional)
        """
        self.max_messages = max_messages
        self.summary_threshold = summary_threshold
        self.client = client

        # Current conversation
        self.messages: list[ConversationTurn] = []

        # Summarized history
        self.summaries: list[str] = []

        # Running summary of the entire session
        self.session_summary: str = ""

        # Context information
        self.context: ContextInfo = ContextInfo()

        # System prompt
        self._system_prompt: str = ""

    @property
    def system_prompt(self) -> str:
        """Get the current system prompt."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set the system prompt."""
        self._system_prompt = value

    def add_user_message(self, content: str, metadata: dict | None = None) -> None:
        """Add a user message to the conversation.

        Args:
            content: Message content
            metadata: Optional metadata (e.g., player name, character name)
        """
        turn = ConversationTurn(
            role="user",
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(turn)
        self._maybe_summarize()

    def add_assistant_message(self, content: str, metadata: dict | None = None) -> None:
        """Add an assistant (DM) message to the conversation.

        Args:
            content: Message content
            metadata: Optional metadata
        """
        turn = ConversationTurn(
            role="assistant",
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(turn)

    def add_system_message(self, content: str) -> None:
        """Add a system message (for injecting context).

        Args:
            content: System message content
        """
        turn = ConversationTurn(role="system", content=content)
        self.messages.append(turn)

    def get_messages_for_llm(self, include_context: bool = True) -> list[Message]:
        """Get messages formatted for the LLM.

        Args:
            include_context: Whether to include context information

        Returns:
            List of Messages for the LLM
        """
        messages = []

        # Build system prompt with context
        system_content = self._system_prompt

        if include_context:
            context_str = self.context.to_context_string()
            if context_str:
                system_content += f"\n\n--- CURRENT CONTEXT ---\n{context_str}"

            if self.session_summary:
                system_content += f"\n\n--- SESSION SUMMARY ---\n{self.session_summary}"

        if system_content:
            messages.append(Message(role="system", content=system_content))

        # Add recent messages
        recent = self.messages[-self.max_messages:]
        for turn in recent:
            messages.append(turn.to_message())

        return messages

    def _maybe_summarize(self) -> None:
        """Check if we need to summarize older messages."""
        if len(self.messages) >= self.summary_threshold and self.client:
            self._generate_summary()

    def _generate_summary(self) -> None:
        """Generate a summary of older messages and trim the history."""
        if not self.client or len(self.messages) < self.summary_threshold:
            return

        # Get messages to summarize (all but the most recent few)
        to_summarize = self.messages[:-5]
        if not to_summarize:
            return

        # Build a prompt for summarization
        conversation_text = "\n".join(
            f"{turn.role.upper()}: {turn.content}"
            for turn in to_summarize
        )

        summary_prompt = f"""Summarize the following game session conversation in 2-3 paragraphs.
Focus on:
- Key events and decisions
- Important NPC interactions
- Combat outcomes
- Quest progress
- Character development moments

CONVERSATION:
{conversation_text}

SUMMARY:"""

        try:
            result = self.client.generate(
                summary_prompt,
                config=GenerationConfig(temperature=0.3, max_tokens=500),
            )
            summary = result.content.strip()

            # Store the summary
            self.summaries.append(summary)

            # Update session summary
            self._update_session_summary(summary)

            # Trim old messages, keep only recent ones
            self.messages = self.messages[-5:]

        except Exception as e:
            # If summarization fails, just trim without summary
            print(f"Warning: Failed to generate summary: {e}")
            self.messages = self.messages[-self.max_messages:]

    def _update_session_summary(self, new_summary: str) -> None:
        """Update the running session summary.

        Args:
            new_summary: New summary to incorporate
        """
        if not self.session_summary:
            self.session_summary = new_summary
            return

        if not self.client:
            # Without LLM, just append
            self.session_summary += f"\n\n{new_summary}"
            return

        # Use LLM to combine summaries
        combine_prompt = f"""Combine these two summaries of a game session into a single coherent summary.
Keep the most important events and details. Maximum 3 paragraphs.

PREVIOUS SUMMARY:
{self.session_summary}

NEW EVENTS:
{new_summary}

COMBINED SUMMARY:"""

        try:
            result = self.client.generate(
                combine_prompt,
                config=GenerationConfig(temperature=0.3, max_tokens=600),
            )
            self.session_summary = result.content.strip()
        except Exception:
            # Fallback: just append
            self.session_summary += f"\n\n{new_summary}"

    def update_context(self, **kwargs) -> None:
        """Update context information.

        Args:
            **kwargs: Context fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

    def clear(self) -> None:
        """Clear all conversation history but keep context."""
        self.messages.clear()
        self.summaries.clear()
        self.session_summary = ""

    def export_history(self) -> dict[str, Any]:
        """Export the full conversation history for saving.

        Returns:
            Dictionary with full history data
        """
        return {
            "messages": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": turn.metadata,
                }
                for turn in self.messages
            ],
            "summaries": self.summaries,
            "session_summary": self.session_summary,
            "system_prompt": self._system_prompt,
        }

    def import_history(self, data: dict[str, Any]) -> None:
        """Import conversation history from saved data.

        Args:
            data: Previously exported history data
        """
        self.messages = [
            ConversationTurn(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {}),
            )
            for m in data.get("messages", [])
        ]
        self.summaries = data.get("summaries", [])
        self.session_summary = data.get("session_summary", "")
        self._system_prompt = data.get("system_prompt", "")

    def get_full_log(self) -> list[dict[str, Any]]:
        """Get the full conversation log for display/export.

        Returns:
            List of message dictionaries
        """
        return [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat(),
                "metadata": turn.metadata,
            }
            for turn in self.messages
        ]
