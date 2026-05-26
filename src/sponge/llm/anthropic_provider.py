"""Anthropic Claude provider — streaming implementation."""

import logging
from collections.abc import AsyncIterator

from sponge.config.settings import Settings
from sponge.cost.models import Usage
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.utils.errors import ProviderError

logger = logging.getLogger("sponge.llm.anthropic")


class AnthropicProvider(LLMProvider):
    """LLM provider for Anthropic Claude models with streaming support."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.model
        self._api_key = settings.anthropic_api_key

    async def stream(
        self,
        messages: list[Message],
        **kwargs: object,
    ) -> AsyncIterator[ContentDelta | UsageEvent]:
        if not self._api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not set. Set it via environment variable or config."
            )

        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "The 'anthropic' package is required. "
                "Install it with: pip install sponge-ai[anthropic]"
            ) from exc

        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        # Build system + user messages
        system_prompt = ""
        api_messages: list[dict[str, object]] = []
        for msg in messages:
            if msg.role == "system":
                system_prompt += msg.content + "\n"
            elif msg.images:
                # Anthropic: content blocks with text + images.
                blocks: list[dict[str, object]] = []
                for img in msg.images:
                    if img.startswith("data:"):
                        header, b64data = img.split(",", 1)
                        mime = header.split(";")[0].replace("data:", "")
                    else:
                        mime = "image/png"
                        b64data = img
                    blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": b64data,
                        },
                    })
                if msg.content:
                    blocks.append({"type": "text", "text": msg.content})
                api_messages.append({"role": msg.role, "content": blocks})
            else:
                api_messages.append({"role": msg.role, "content": msg.content})

        try:
            async with client.messages.stream(
                model=self.model,
                system=system_prompt.strip() if system_prompt else anthropic.NOT_GIVEN,
                messages=api_messages,
                max_tokens=kwargs.get("max_tokens", 4096),
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        text = getattr(event.delta, "text", "")
                        if text:
                            yield ContentDelta(text=text)

                # After stream ends, get final usage.
                final = await stream.get_final_message()
                usage = Usage(
                    tokens_in=final.usage.input_tokens,
                    tokens_out=final.usage.output_tokens,
                    cache_read_tokens=getattr(final.usage, "cache_read_input_tokens", 0),
                    cache_write_tokens=getattr(final.usage, "cache_creation_input_tokens", 0),
                )
                yield UsageEvent(usage=usage)

        except anthropic.APIError as e:
            raise ProviderError(f"Anthropic API error: {e}") from e
