"""Generic state machine transition validator."""

from __future__ import annotations

from enum import StrEnum
from typing import Generic, TypeVar

S = TypeVar("S", bound=StrEnum)


class StateMachine(Generic[S]):
    """Validates state transitions against a defined transition map."""

    def __init__(self, transitions: dict[S, set[S]]) -> None:
        self._transitions = transitions

    def validate(self, current: S, target: S) -> S:
        """Validate and return the target state.

        Raises ``ValueError`` if the transition is not allowed.
        """
        allowed = self._transitions.get(current, set())
        if target not in allowed:
            raise ValueError(
                f"Invalid transition: {current} -> {target}. "
                f"Allowed: {', '.join(s.value for s in allowed) or 'none (terminal)'}"
            )
        return target
