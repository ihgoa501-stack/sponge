"""OpenAI provider — streaming implementation."""

import logging
from collections.abc import AsyncIterator

from sponge.config.settings import Settings
from sponge.cost.models import Usage
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.utils.errors import ProviderError

logger = logging.getLogger("sponge.llm.openai")


class OpenAIProvider(LLMProvider):
    """LLM provider for OpenAI models (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = settings.model
        self._api_key = settings.openai_api_key

    async def stream(
        self,
        messages: list[Message],
        **kwargs: object,
    ) -> AsyncIterator[ContentDelta | UsageEvent]:
        if not self._api_key:
            raise ProviderError("OPENAI_API_KEY is not set. Set it via environment variable.")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderError(
                "The 'openai' package is required. Install with: pip install openai"
            ) from exc

        client = AsyncOpenAI(api_key=self._api_key)

        api_messages: list[dict[str, object]] = []
        for m in messages:
            if m.images:
                # OpenAI: content array with text + image_url blocks.
                blocks: list[dict[str, object]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for img in m.images:
                    blocks.append({"type": "image_url", "image_url": {"url": img}})
                api_messages.append({"role": m.role, "content": blocks})
            else:
                api_messages.append({"role": m.role, "content": m.content})

        try:
            stream = await client.chat.completions.create(
                model=self._model,
                messages=api_messages,
                stream=True,
                stream_options={"include_usage": True},
                max_tokens=kwargs.get("max_tokens", 4096),
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield ContentDelta(text=chunk.choices[0].delta.content)

                if chunk.usage:
                    yield UsageEvent(
                        usage=Usage(
                            tokens_in=chunk.usage.prompt_tokens,
                            tokens_out=chunk.usage.completion_tokens,
                            cache_read_tokens=getattr(chunk.usage, "prompt_tokens_details", None)
                            and getattr(
                                chunk.usage.prompt_tokens_details,
                                "cached_tokens",
                                0,
                            )
                            or 0,
                        )
                    )

        except Exception as e:
            raise ProviderError(f"OpenAI API error: {e}") from e
