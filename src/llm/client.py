"""LLM client wrappers with streaming support for AI Dungeon Master."""

import asyncio
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Iterator, Optional

from openai import AsyncOpenAI, OpenAI
from ollama import AsyncClient, Client


@dataclass
class Message:
    """A message in the conversation."""

    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary for Ollama API."""
        return {"role": self.role, "content": self.content}


@dataclass
class GenerationConfig:
    """Configuration for text generation."""

    temperature: float = 0.8
    max_tokens: int = 1024
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of a text generation."""

    content: str
    model: str
    done: bool = True
    total_duration: int | None = None  # nanoseconds
    prompt_eval_count: int | None = None  # tokens in prompt
    eval_count: int | None = None  # tokens generated


class OllamaClient:
    """Wrapper around Ollama client with conversation management."""

    def __init__(
        self,
        model: str = "hermes3:latest",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        """Initialize the Ollama client.

        Args:
            model: Model name to use
            base_url: Ollama server URL
            timeout: Request timeout in seconds
        """
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

        # Synchronous client
        self._client = Client(host=base_url, timeout=timeout)

        # Async client
        self._async_client = AsyncClient(host=base_url, timeout=timeout)

    def is_available(self) -> bool:
        """Check if Ollama server is available and model is loaded.

        Returns:
            True if server is available and model exists
        """
        try:
            response = self._client.list()
            # Handle both dict and object responses from ollama client
            if hasattr(response, 'models'):
                model_names = [m.model for m in response.models]
            else:
                model_names = [m.get("name", m.get("model", "")) for m in response.get("models", [])]
            # Check for exact match or base name match
            base_model = self.model.split(":")[0]
            return any(
                self.model in name or base_model in name
                for name in model_names
            )
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models on the Ollama server.

        Returns:
            List of model names
        """
        try:
            response = self._client.list()
            # Handle both dict and object responses from ollama client
            if hasattr(response, 'models'):
                return [m.model for m in response.models]
            else:
                return [m.get("name", m.get("model", "")) for m in response.get("models", [])]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Generate a response from a prompt (non-streaming).

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self._client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        return GenerationResult(
            content=response["message"]["content"],
            model=response.get("model", self.model),
            done=response.get("done", True),
            total_duration=response.get("total_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> Iterator[str]:
        """Generate a streaming response from a prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Yields:
            String chunks as they are generated
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]

    def chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Generate a response from a conversation (non-streaming).

        Args:
            messages: List of conversation messages
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()

        response = self._client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        return GenerationResult(
            content=response["message"]["content"],
            model=response.get("model", self.model),
            done=response.get("done", True),
            total_duration=response.get("total_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

    def chat_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Generate a streaming response from a conversation.

        Args:
            messages: List of conversation messages
            config: Generation configuration
            on_token: Optional callback called for each token

        Returns:
            Complete response text
        """
        config = config or GenerationConfig()
        full_response = []

        stream = self._client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                token = chunk["message"]["content"]
                full_response.append(token)
                if on_token:
                    on_token(token)

        return "".join(full_response)

    async def agenerate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Async generate a response from a prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self._async_client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        return GenerationResult(
            content=response["message"]["content"],
            model=response.get("model", self.model),
            done=response.get("done", True),
            total_duration=response.get("total_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

    async def agenerate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """Async generate a streaming response.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Yields:
            String chunks as they are generated
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = await self._async_client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        async for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]

    async def achat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Async generate a response from a conversation.

        Args:
            messages: List of conversation messages
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()

        response = await self._async_client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        return GenerationResult(
            content=response["message"]["content"],
            model=response.get("model", self.model),
            done=response.get("done", True),
            total_duration=response.get("total_duration"),
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

    async def achat_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """Async streaming chat response.

        Args:
            messages: List of conversation messages
            config: Generation configuration

        Yields:
            String chunks as they are generated
        """
        config = config or GenerationConfig()

        stream = await self._async_client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            options={
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "stop": config.stop if config.stop else None,
            },
        )

        async for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                yield chunk["message"]["content"]


class OpenAIClient:
    """Wrapper around OpenAI client with conversation management."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        """Initialize the OpenAI client.

        Args:
            model: Model name to use (e.g., gpt-4o-mini, gpt-4o)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout = timeout

        # Synchronous client
        self._client = OpenAI(api_key=self.api_key, timeout=timeout)

        # Async client
        self._async_client = AsyncOpenAI(api_key=self.api_key, timeout=timeout)

    def is_available(self) -> bool:
        """Check if OpenAI API is available and key is valid.

        Returns:
            True if API is accessible
        """
        if not self.api_key:
            return False
        try:
            # Simple API test - list models
            self._client.models.list()
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models on OpenAI.

        Returns:
            List of model names
        """
        try:
            response = self._client.models.list()
            return [m.id for m in response.data]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Generate a response from a prompt (non-streaming).

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,  # OpenAI uses 0-2 range
            stop=config.stop if config.stop else None,
        )

        return GenerationResult(
            content=response.choices[0].message.content or "",
            model=response.model,
            done=True,
            prompt_eval_count=response.usage.prompt_tokens if response.usage else None,
            eval_count=response.usage.completion_tokens if response.usage else None,
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> Iterator[str]:
        """Generate a streaming response from a prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Yields:
            String chunks as they are generated
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Generate a response from a conversation (non-streaming).

        Args:
            messages: List of conversation messages
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        return GenerationResult(
            content=response.choices[0].message.content or "",
            model=response.model,
            done=True,
            prompt_eval_count=response.usage.prompt_tokens if response.usage else None,
            eval_count=response.usage.completion_tokens if response.usage else None,
        )

    def chat_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Generate a streaming response from a conversation.

        Args:
            messages: List of conversation messages
            config: Generation configuration
            on_token: Optional callback called for each token

        Returns:
            Complete response text
        """
        config = config or GenerationConfig()
        full_response = []

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response.append(token)
                if on_token:
                    on_token(token)

        return "".join(full_response)

    async def agenerate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Async generate a response from a prompt.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        return GenerationResult(
            content=response.choices[0].message.content or "",
            model=response.model,
            done=True,
            prompt_eval_count=response.usage.prompt_tokens if response.usage else None,
            eval_count=response.usage.completion_tokens if response.usage else None,
        )

    async def agenerate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """Async generate a streaming response.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            config: Generation configuration

        Yields:
            String chunks as they are generated
        """
        config = config or GenerationConfig()
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        stream = await self._async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def achat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Async generate a response from a conversation.

        Args:
            messages: List of conversation messages
            config: Generation configuration

        Returns:
            GenerationResult with the response
        """
        config = config or GenerationConfig()

        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        return GenerationResult(
            content=response.choices[0].message.content or "",
            model=response.model,
            done=True,
            prompt_eval_count=response.usage.prompt_tokens if response.usage else None,
            eval_count=response.usage.completion_tokens if response.usage else None,
        )

    async def achat_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """Async streaming chat response.

        Args:
            messages: List of conversation messages
            config: Generation configuration

        Yields:
            String chunks as they are generated
        """
        config = config or GenerationConfig()

        stream = await self._async_client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            stream=True,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.repeat_penalty - 1.0,
            stop=config.stop if config.stop else None,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
