"""Agent — the core orchestrator (~30 lines)."""

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sponge.cache.result_cache import ResultCache
from sponge.config.settings import Settings
from sponge.core.context import ContextCompressor
from sponge.core.session import Session, Turn
from sponge.core.task import Task, TaskResult
from sponge.cost.models import CostEntry, Usage
from sponge.cost.pricing import get_model_pricing
from sponge.cost.tracker import CostTracker
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.llm.token_counter import count_tokens
from sponge.plugins.registry import PluginRegistry
from sponge.telemetry.collector import TelemetryCollector
from sponge.telemetry.models import CostFingerprint

logger = logging.getLogger("sponge.core.agent")


class Agent:
    """Executes tasks through an LLM provider with caching and cost tracking.

    The core loop is intentionally tiny — infrastructure does the heavy lifting.
    """

    def __init__(
        self,
        provider: LLMProvider,
        settings: Settings,
        cache: ResultCache,
        collector: TelemetryCollector,
        plugins: PluginRegistry | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._cache = cache
        self._collector = collector
        self._plugins = plugins

    async def run(
        self,
        task: Task,
        *,
        experiment_id: str | None = None,
        experiment_group: str | None = None,
    ) -> TaskResult:
        """Execute a task and return the result with cost breakdown.

        1. Check exact cache → return cached if hit.
        2. Stream from provider.
        3. Record cost + fingerprint.
        4. Write to cache.
        """
        model = task.model or self._settings.model
        session_id = uuid.uuid4().hex[:12]
        task_hash = hashlib.sha256(task.prompt.encode()).hexdigest()[:16]

        # 0. Plugin routing — bypass LLM entirely if a plugin can handle this.
        if self._plugins is not None:
            match = self._plugins.best_match(task.prompt)
            if match and match.confidence >= 0.8:
                logger.info("Plugin match: %s (%.0f%%)", match.plugin.name, match.confidence * 100)
                from sponge.plugins.base import PluginContext

                plugin_result = await self._plugins.execute(match, PluginContext(task=task.prompt))
                entry = CostEntry(
                    usage=Usage(tokens_in=0, tokens_out=0),
                    model=model,
                    cost=0.0,
                    naive_cost=0.01,  # rough estimate of LLM cost
                )
                fp = self._make_fingerprint(
                    session_id=session_id,
                    task_hash=task_hash,
                    model=model,
                    cost_entry=entry,
                    cache_hit=False,
                )
                self._collector.log_call(fp)
                return TaskResult(
                    task=task,
                    response=plugin_result.output,
                    cost_entry=entry,
                    fingerprint=fp,
                    cache_hit=False,
                )

        # 1. Check exact cache.
        cached = self._cache.get(task.prompt, model, task.system_prompt)
        if cached is not None:
            logger.info("Cache hit for task hash=%s", task_hash)
            entry = self._make_cache_hit_entry(model)
            fp = self._make_fingerprint(
                session_id=session_id,
                task_hash=task_hash,
                model=model,
                cost_entry=entry,
                cache_hit=True,
                experiment_id=experiment_id,
                experiment_group=experiment_group,
            )
            self._collector.log_call(fp)
            return TaskResult(
                task=task,
                response=cached,
                cost_entry=entry,
                fingerprint=fp,
                cache_hit=True,
            )

        # 2. Stream from provider.
        messages = self._build_messages(task)
        response_chunks: list[str] = []
        tracker = CostTracker(get_model_pricing(self._settings.provider, model))

        async for event in self._provider.stream(messages):
            match event:
                case ContentDelta(text=text):
                    response_chunks.append(text)
                case UsageEvent(usage=usage):
                    tracker.record_usage(usage)

        response = "".join(response_chunks)
        cost_entry = tracker.finalize(model)

        # 3. Record fingerprint.
        fp = self._make_fingerprint(
            session_id=session_id,
            task_hash=task_hash,
            model=model,
            cost_entry=cost_entry,
            cache_hit=False,
            experiment_id=experiment_id,
            experiment_group=experiment_group,
        )
        self._collector.log_call(fp)

        # 4. Write to cache.
        self._cache.set(task.prompt, model, task.system_prompt, response)

        logger.info(
            "Call complete: cost=$%.6f naive=$%.6f",
            cost_entry.cost,
            cost_entry.naive_cost,
        )
        return TaskResult(
            task=task,
            response=response,
            cost_entry=cost_entry,
            fingerprint=fp,
            cache_hit=False,
        )

    async def run_with_history(
        self,
        session: Session,
        user_message: str,
        *,
        max_history: int = 20,
        experiment_id: str | None = None,
        experiment_group: str | None = None,
    ) -> TaskResult:
        """Run a turn within an existing session, using conversation history.

        Compresses history to the most recent `max_history` turns (sliding window),
        prepends system turns, sends to provider, and appends the result to the session.
        """
        model = session.model or self._settings.model
        session_id = session.id

        # Build messages from recent history + new user message.
        recent = session.recent_turns(max_history)
        messages = [Message(role=t.role, content=t.content) for t in recent]
        messages.append(Message(role="user", content=user_message))

        # Compress context if history is large.
        pre_tokens = count_tokens("".join(m.content for m in messages), model)
        compressor = ContextCompressor(
            provider=self._provider,
            token_budget=self._settings.context_token_budget,
            counter=lambda text: count_tokens(text, model),
        )
        messages = await compressor.compress(messages)
        post_tokens = count_tokens("".join(m.content for m in messages), model)
        ratio = (post_tokens / pre_tokens * 100) if pre_tokens > 0 else 100
        logger.debug(
            "Compression: %d → %d tokens (%.0f%%)",
            pre_tokens,
            post_tokens,
            ratio,
        )

        # Stream from provider.
        response_chunks: list[str] = []
        tracker = CostTracker(get_model_pricing(self._settings.provider, model))

        async for event in self._provider.stream(messages):
            match event:
                case ContentDelta(text=text):
                    response_chunks.append(text)
                case UsageEvent(usage=usage):
                    tracker.record_usage(usage)

        response = "".join(response_chunks)
        cost_entry = tracker.finalize(model)

        # Append turns to session.
        session.add_turn(Turn(role="user", content=user_message))
        session.add_turn(
            Turn(
                role="assistant",
                content=response,
                cost=cost_entry.cost,
                cache_hit=False,
            )
        )

        # Record fingerprint.
        fp = self._make_fingerprint(
            session_id=session_id,
            task_hash=str(hash(user_message)) if user_message else "",
            model=model,
            cost_entry=cost_entry,
            cache_hit=False,
            experiment_id=experiment_id,
            experiment_group=experiment_group,
        )
        self._collector.log_call(fp)

        logger.info(
            "Session turn: cost=$%.6f naive=$%.6f (history: %d turns)",
            cost_entry.cost,
            cost_entry.naive_cost,
            len(recent),
        )

        task = Task(prompt=user_message, model=model)
        return TaskResult(
            task=task,
            response=response,
            cost_entry=cost_entry,
            fingerprint=fp,
            cache_hit=False,
        )

    def _build_messages(self, task: Task) -> list[Message]:
        messages: list[Message] = []
        if task.system_prompt:
            messages.append(Message(role="system", content=task.system_prompt))
        messages.append(Message(role="user", content=task.prompt))
        return messages

    def _make_cache_hit_entry(self, model: str) -> CostEntry:
        return CostEntry(
            usage=Usage(tokens_in=0, tokens_out=0),
            model=model,
            cost=0.0,
            naive_cost=0.0,
        )

    def _make_fingerprint(
        self,
        session_id: str,
        task_hash: str,
        model: str,
        cost_entry: CostEntry,
        cache_hit: bool,
        experiment_id: str | None = None,
        experiment_group: str | None = None,
    ) -> CostFingerprint:
        import subprocess

        try:
            repo = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            repo = ""

        return CostFingerprint(
            session_id=session_id,
            task_hash=task_hash,
            model=model,
            provider=self._settings.provider,
            tokens_in=cost_entry.usage.tokens_in,
            tokens_out=cost_entry.usage.tokens_out,
            cache_hit=cache_hit,
            cost=cost_entry.cost,
            naive_cost=cost_entry.naive_cost,
            repo_state=repo,
            timestamp=datetime.now(UTC).isoformat(),
            experiment_id=experiment_id,
            experiment_group=experiment_group,
        )
