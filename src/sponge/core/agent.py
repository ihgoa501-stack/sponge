"""Agent — the core orchestrator (~30 lines)."""

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sponge.cache.result_cache import ResultCache
from sponge.cache.semantic_cache import SemanticCache
from sponge.config.settings import Settings
from sponge.core.condenser import CondensedResult, SubAgentCondenser
from sponge.core.context import ContextCompressor
from sponge.core.context_planner import ContextPlanner
from sponge.core.decomposer import TaskDecomposer
from sponge.core.reflection import Lesson, ReflectionModule
from sponge.core.session import Session, Turn
from sponge.core.task import Task, TaskResult
from sponge.cost.models import CostEntry, Usage
from sponge.cost.pricing import get_model_pricing
from sponge.cost.tracker import CostTracker
from sponge.llm.base import ContentDelta, LLMProvider, Message, UsageEvent
from sponge.llm.token_counter import count_tokens
from sponge.memory.reflective import ReflectiveMemory
from sponge.memory.store import ProjectMemory
from sponge.plugins.registry import PluginRegistry
from sponge.telemetry.collector import TelemetryCollector
from sponge.telemetry.models import CostFingerprint
from sponge.utils.retry import retry

logger = logging.getLogger("sponge.core.agent")


@dataclass
class AgentServices:
    """Optional services that extend the agent with Phase 2+ capabilities."""

    plugins: PluginRegistry | None = None
    decomposer: TaskDecomposer | None = None
    condenser: SubAgentCondenser | None = None
    context_planner: ContextPlanner | None = None
    semantic_cache: SemanticCache | None = None
    memory: ProjectMemory | None = None
    reflective_memory: ReflectiveMemory | None = None
    """Phase 7: stores lessons extracted from failures."""
    reflection_module: ReflectionModule | None = None
    """Phase 7: the bronze mirror — generates structured self-evaluation."""


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
        services: AgentServices | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._cache = cache
        self._collector = collector
        self._svc = services or AgentServices()

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
        if self._svc.plugins is not None:
            match = self._svc.plugins.best_match(task.prompt)
            if match and match.confidence >= 0.8:
                from sponge.plugins.base import ApprovalLevel, PluginContext

                # Check approval level (per-match overrides per-plugin default).
                approval = match.approval or match.plugin.approval
                if approval == ApprovalLevel.REJECT:
                    logger.info("Plugin %s rejected by policy", match.plugin.name)
                elif (
                    approval == ApprovalLevel.CONFIRM
                    and not self._settings.auto_approve
                ):
                    logger.info(
                        "Plugin %s requires confirmation (use --auto-approve)", match.plugin.name
                    )
                else:
                    logger.info(
                        "Plugin match: %s (%.0f%%), executing",
                        match.plugin.name,
                        match.confidence * 100,
                    )
                    plugin_result = await self._svc.plugins.execute(
                        match, PluginContext(task=task.prompt)
                    )
                    entry = CostEntry(
                        usage=Usage(tokens_in=0, tokens_out=0),
                        model=model,
                        cost=0.0,
                        naive_cost=0.01,
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
            cached_response, original_cost = cached
            logger.info("Cache hit for task hash=%s", task_hash)
            entry = self._make_cache_hit_entry(model, naive_cost=original_cost)
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
                response=cached_response,
                cost_entry=entry,
                fingerprint=fp,
                cache_hit=True,
                cache_source="exact",
            )

        # 1.5. Check semantic cache.
        if self._svc.semantic_cache is not None:
            sem_cached = self._svc.semantic_cache.get(task.prompt)
            if sem_cached is not None:
                logger.info("Semantic cache hit for task hash=%s", task_hash)
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
                    response=sem_cached,
                    cost_entry=entry,
                    fingerprint=fp,
                    cache_hit=True,
                    cache_source="semantic",
                )

        # 1.7. Retrieve relevant lessons from reflective memory.
        lessons_context = ""
        lessons_retrieved = 0
        if self._svc.reflective_memory is not None:
            lessons_context = self._svc.reflective_memory.to_context(task.prompt)
            if lessons_context:
                lessons_retrieved = lessons_context.count("[ref_")
                logger.debug("Retrieved %d lessons for task", lessons_retrieved)

        # 2. Stream from provider (with retry).
        messages = self._build_messages(task, lessons_context)
        response, cost_entry = await self._stream_with_retry(messages, model)

        # 2.5. Reflect on failure if reflective memory is configured.
        lesson_stored = ""
        reflection_tokens = 0
        if task.failed and self._svc.reflection_module is not None:
            logger.info("Task failed — triggering reflection")
            reflection_result = await self._svc.reflection_module.reflect(
                task_prompt=task.prompt,
                messages=messages,
                response=response,
                failure_reason=task.failure_reason or "Task was marked as failed.",
                model=model,
            )
            if reflection_result is not None:
                from sponge.core.reflection import extract_lesson

                lesson = extract_lesson(
                    reflection_result,
                    task.prompt,
                    condition_tags=_derive_condition_tags(task),
                )
                if self._svc.reflective_memory is not None:
                    stored = self._svc.reflective_memory.store(lesson)
                    lesson_stored = stored.id
                    logger.info("Stored lesson %s: %s", stored.id, lesson.lesson)
                reflection_tokens = ReflectionModule.ESTIMATED_TOKENS

        # 3. Record fingerprint.
        fp = self._make_fingerprint(
            session_id=session_id,
            task_hash=task_hash,
            model=model,
            cost_entry=cost_entry,
            cache_hit=False,
            experiment_id=experiment_id,
            experiment_group=experiment_group,
            reflection_tokens=reflection_tokens,
            lessons_retrieved=lessons_retrieved,
            lesson_stored=lesson_stored,
        )
        self._collector.log_call(fp)

        # 4. Write to caches.
        self._cache.set(task.prompt, model, task.system_prompt, response, cost=cost_entry.cost)
        if self._svc.semantic_cache is not None:
            self._svc.semantic_cache.set(task.prompt, response)

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
            failed=task.failed,
            failure_reason=task.failure_reason,
            lesson_stored=lesson_stored,
        )

    async def run_decomposed(self, task: Task) -> TaskResult:
        """Execute a task with architecture-level token reduction.

        Flow:
        1. Decompose complex task → sub-tasks (if applicable)
        2. Plan context per sub-task → load only what's needed
        3. Execute each sub-task
        4. Condense results → structured summary
        5. Record fingerprints per step

        If no decomposer is configured, falls back to regular run().
        """
        if self._svc.decomposer is None:
            return await self.run(task)

        model = task.model or self._settings.model

        # 1. Decompose.
        decompose_result = await self._svc.decomposer.decompose(task.prompt)

        if not decompose_result.was_decomposed or len(decompose_result.sub_tasks) <= 1:
            return await self.run(task)

        # 2-3. Execute each sub-task with context planning.
        results: list[str] = []
        total_cost = 0.0
        total_naive = 0.0
        total_in = 0
        total_out = 0

        for st in decompose_result.sub_tasks:
            # Plan context.
            ctx_items: list[str] = []
            if self._svc.context_planner is not None:
                plan = self._svc.context_planner.plan(st.id, st.description, st.context_hint)
                ctx_items = [item.path for item in plan.needed]

            # Execute sub-task (cheap LLM call with minimal context).
            sub_prompt = st.description
            if ctx_items:
                sub_prompt = f"Context files: {', '.join(ctx_items[:5])}\n\n{st.description}"

            sub_result = await self.run(Task(prompt=sub_prompt, model=model))
            results.append(sub_result.response)
            total_cost += sub_result.cost_entry.cost
            total_naive += sub_result.cost_entry.naive_cost
            total_in += sub_result.cost_entry.usage.tokens_in
            total_out += sub_result.cost_entry.usage.tokens_out

            # Mark context as loaded.
            if self._svc.context_planner is not None:
                self._svc.context_planner.mark_loaded(ctx_items)

        # 4. Condense results.
        raw_output = "\n\n".join(
            f"Sub-task {st.id}: {r}"
            for st, r in zip(decompose_result.sub_tasks, results, strict=False)
        )

        condensed: CondensedResult | None = None
        if self._svc.condenser is not None:
            condensed = await self._svc.condenser.condense(raw_output)

        session_id = uuid.uuid4().hex[:12]
        task_hash = hashlib.sha256(task.prompt.encode()).hexdigest()[:16]

        if condensed and condensed.findings:
            final_response = f"{condensed.summary}\n\n{condensed.key_insight}"
        else:
            final_response = "\n\n".join(results)

        cost_entry = CostEntry(
            usage=Usage(
                tokens_in=total_in,
                tokens_out=total_out,
            ),
            model=model,
            cost=round(total_cost, 6),
            naive_cost=round(total_naive, 6),
        )
        fp = self._make_fingerprint(
            session_id=session_id,
            task_hash=task_hash,
            model=model,
            cost_entry=cost_entry,
            cache_hit=False,
        )
        self._collector.log_call(fp)

        logger.info(
            "Decomposed: %d sub-tasks, cost=$%.4f naive=$%.4f",
            len(decompose_result.sub_tasks),
            total_cost,
            total_naive,
        )
        return TaskResult(
            task=task,
            response=final_response,
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

        # Stream from provider (with retry).
        model_name = session.model or self._settings.model
        response, cost_entry = await self._stream_with_retry(messages, model_name)

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
            task_hash=(
                str(hashlib.md5(user_message.encode()).hexdigest()[:16])
                if user_message else ""
            ),
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

    def _build_messages(
        self, task: Task, lessons_context: str = ""
    ) -> list[Message]:
        messages: list[Message] = []
        # Inject reflective lessons first (highest priority context).
        if lessons_context:
            messages.append(Message(role="system", content=lessons_context))
        # Inject project memory as system message.
        if self._svc.memory is not None:
            mem_prompt = self._svc.memory.to_system_prompt()
            if mem_prompt:
                messages.append(Message(role="system", content=mem_prompt))
        if task.system_prompt:
            messages.append(Message(role="system", content=task.system_prompt))
        user_msg = Message(role="user", content=task.prompt)
        if task.images:
            user_msg.images = task.images
        messages.append(user_msg)
        return messages

    async def _stream_with_retry(
        self, messages: list[Message], model: str
    ) -> tuple[str, CostEntry]:
        """Stream from provider with retry on transient errors."""

        async def _do_stream() -> tuple[str, CostEntry]:
            chunks: list[str] = []
            tracker = CostTracker(get_model_pricing(self._settings.provider, model))
            try:
                async for event in self._provider.stream(messages):
                    match event:
                        case ContentDelta(text=text):
                            chunks.append(text)
                        case UsageEvent(usage=usage):
                            tracker.record_usage(usage)
            except KeyboardInterrupt:
                logger.info("Stream interrupted by user")
                if chunks:
                    chunks.append("\n\n[interrupted]")
            except asyncio.CancelledError:
                logger.info("Stream cancelled by user")
                if chunks:
                    chunks.append("\n\n[interrupted]")
            return "".join(chunks), tracker.finalize(model)

        return await retry(_do_stream)

    def _make_cache_hit_entry(self, model: str, naive_cost: float = 0.0) -> CostEntry:
        return CostEntry(
            usage=Usage(tokens_in=0, tokens_out=0),
            model=model,
            cost=0.0,
            naive_cost=naive_cost,
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
        reflection_tokens: int = 0,
        lessons_retrieved: int = 0,
        lesson_stored: str = "",
    ) -> CostFingerprint:
        from sponge.cache.repo_state import get_repo_state

        repo = get_repo_state()

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
            reflection_tokens=reflection_tokens,
            lessons_retrieved=lessons_retrieved,
            lesson_stored=lesson_stored,
        )


def _derive_condition_tags(task: Task) -> list[str]:
    """Derive condition tags from a task for lesson keying.

    Heuristic: extract task type and context patterns from the prompt.
    """
    tags: list[str] = []
    prompt_lower = task.prompt.lower()

    # Task type tags.
    if any(w in prompt_lower for w in ("edit", "change", "modify", "update", "fix", "refactor")):
        tags.append("file_edit")
    if any(w in prompt_lower for w in ("test", "pytest", "unittest")):
        tags.append("test")
    if any(w in prompt_lower for w in ("search", "find", "grep", "locate")):
        tags.append("search")
    if any(w in prompt_lower for w in ("run", "execute", "shell", "command")):
        tags.append("shell_cmd")
    if any(w in prompt_lower for w in ("read", "open", "view", "show", "inspect")):
        tags.append("file_read")

    # Failure mode tags (inferred from task.failed context).
    if task.failed:
        if task.failure_reason:
            reason_lower = task.failure_reason.lower()
            if any(w in reason_lower for w in ("test", "pytest", "fail", "error")):
                tags.append("test_breakage")
            if any(w in reason_lower for w in ("wrong", "incorrect", "not what")):
                tags.append("quality_issue")
            if any(w in reason_lower for w in ("timeout", "connection", "rate limit")):
                tags.append("provider_error")

    if not tags:
        tags.append("general")
    return tags
