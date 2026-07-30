"""Versioned, JSON-safe events shared by desktop, browser, replay, and tests.

The current desktop adapter still drives :class:`game.MahjongGame` through its
interactive compatibility layer.  This module deliberately has no dependency
on that UI: a future event-driven engine can emit these records while both
clients consume the same contract.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


EVENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class GameEvent:
    """A deterministic game event with no wall-clock data in its payload."""

    sequence: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: int = EVENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GameEvent":
        version = int(data.get("schema_version", EVENT_SCHEMA_VERSION))
        if version != EVENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported game event schema version: {version}")
        sequence = int(data["sequence"])
        kind = str(data["kind"])
        payload = data.get("payload", {})
        if not isinstance(payload, Mapping):
            raise ValueError("Game event payload must be an object.")
        return cls(sequence, kind, dict(payload), version)


class EventLog:
    """Append-only event collection suitable for a seeded replay file."""

    def __init__(self, events: list[GameEvent] | None = None) -> None:
        self.events = list(events or [])

    def append(self, kind: str, payload: Mapping[str, Any] | None = None) -> GameEvent:
        event = GameEvent(len(self.events), kind, dict(payload or {}))
        # Fail early so a browser/client never receives a non-JSON replay.
        json.dumps(event.to_dict(), ensure_ascii=False)
        self.events.append(event)
        return event

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVENT_SCHEMA_VERSION,
            "events": [event.to_dict() for event in self.events],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EventLog":
        version = int(data.get("schema_version", EVENT_SCHEMA_VERSION))
        if version != EVENT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported event log schema version: {version}")
        raw_events = data.get("events", [])
        if not isinstance(raw_events, list):
            raise ValueError("Event log events must be an array.")
        events = [GameEvent.from_dict(item) for item in raw_events]
        if [event.sequence for event in events] != list(range(len(events))):
            raise ValueError("Event sequence must start at zero and be contiguous.")
        return cls(events)

    @classmethod
    def from_json(cls, value: str) -> "EventLog":
        data = json.loads(value)
        if not isinstance(data, Mapping):
            raise ValueError("Event log JSON root must be an object.")
        return cls.from_dict(data)


def snapshot_event(snapshot: Mapping[str, Any], *, sequence: int = 0) -> GameEvent:
    """Wrap an existing ``MahjongGame.public_snapshot`` in a replay event."""

    return GameEvent(sequence, "state.snapshot", dict(snapshot))
