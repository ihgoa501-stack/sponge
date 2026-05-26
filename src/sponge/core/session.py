"""Session persistence — save and load conversation history.

Sessions are stored as JSONL files at ~/.sponge/sessions/<id>.jsonl.
Each line is a JSON object with role, content, and optional metadata.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SESSIONS_DIR = Path.home() / ".sponge" / "sessions"


@dataclass
class Turn:
    """A single turn in a conversation."""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    cost: float | None = None  # set on assistant turns
    cache_hit: bool = False


@dataclass
class Session:
    """A multi-turn conversation session."""

    id: str
    turns: list[Turn] = field(default_factory=list)
    model: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def total_cost(self) -> float:
        return sum(t.cost or 0.0 for t in self.turns)

    def add_turn(self, turn: Turn) -> None:
        self.turns.append(turn)

    def recent_turns(self, max_turns: int) -> list[Turn]:
        """Return the most recent N turns, always keeping system messages."""
        system_turns = [t for t in self.turns if t.role == "system"]
        other_turns = [t for t in self.turns if t.role != "system"]
        recent = other_turns[-max_turns:] if len(other_turns) > max_turns else other_turns
        return system_turns + recent


def create_session(model: str = "") -> Session:
    """Create a new session with a unique ID."""
    return Session(id=uuid.uuid4().hex[:12], model=model)


def save_session(session: Session) -> None:
    """Persist a session to disk as JSONL."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{session.id}.jsonl"

    lines = []
    for turn in session.turns:
        lines.append(
            json.dumps(
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp,
                    "cost": turn.cost,
                    "cache_hit": turn.cache_hit,
                }
            )
        )
    path.write_text("\n".join(lines) + "\n")


def load_session(session_id: str) -> Session | None:
    """Load a session from disk. Returns None if not found."""
    path = SESSIONS_DIR / f"{session_id}.jsonl"
    if not path.is_file():
        return None

    turns = []
    for line in path.read_text().strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        turns.append(
            Turn(
                role=data["role"],
                content=data["content"],
                timestamp=data.get("timestamp", ""),
                cost=data.get("cost"),
                cache_hit=data.get("cache_hit", False),
            )
        )

    # Infer model from first assistant turn metadata, or empty.
    model = ""

    return Session(id=session_id, turns=turns, model=model)


def list_sessions() -> list[dict[str, object]]:
    """List all saved sessions with summary stats."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        sid = path.stem
        try:
            session = load_session(sid)
            if session is None:
                continue
            sessions.append(
                {
                    "id": sid,
                    "turns": len(session.turns),
                    "total_cost": session.total_cost,
                    "created_at": session.created_at,
                }
            )
        except Exception:
            continue
    return sessions
