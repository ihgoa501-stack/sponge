"""DeepSeek provider — OpenAI-compatible API at deepseek endpoints."""

import logging
from collections.abc import AsyncIterator

from sponge.config.settings import Settings
from sponge.cost.models import Usage
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.utils.errors import ProviderError

logger = logging.getLogger("sponge.llm.deepseek")


class DeepSeekProvider(LLMProvider):
    """LLM provider for DeepSeek models (V3, R1) via OpenAI-compatible API."""

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = settings.model
        self._api_key = settings.deepseek_api_key

    async def stream(
        self,
        messages: list[Message],
        **kwargs: object,
    ) -> AsyncIterator[ContentDelta | UsageEvent]:
        if not self._api_key:
            raise ProviderError("DEEPSEEK_API_KEY is not set. Set it via environment variable.")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ProviderError(
                "The 'openai' package is required. Install with: pip install openai"
            ) from exc

        client = AsyncOpenAI(api_key=self._api_key, base_url=self.BASE_URL)

        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            stream = await client.chat.completions.create(
                model=self._model,
                messages=api_messages,
                stream=True,
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
                        )
                    )

        except Exception as e:
            raise ProviderError(f"DeepSeek API error: {e}") from e
