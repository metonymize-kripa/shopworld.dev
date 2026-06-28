"""Merchant adapter interface.

An adapter drives the thing under test and returns structured observations.
Two concrete adapters share this interface:

  * ``AgentAdapter`` -- conversational merchants (chat/API/MCP). Merchant turns
    are messages.
  * ``WebAdapter`` -- form-driven storefronts. "Merchant turns" are page
    states and shopper "utterances" are DOM actions. The same dialogue policy
    drives both.

Adapters are deliberately thin: they translate between the abstract dialogue
(utterances <-> merchant responses) and the concrete transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class MerchantTurn:
    """A structured observation of one merchant response."""

    text: str
    # Structured signals an adapter can extract cheaply (DOM fields, buttons,
    # status codes). Used by the turn classifier alongside the text.
    has_question: bool = False
    has_action_button: bool = False
    fields: dict[str, str] = field(default_factory=dict)
    raw: dict | None = None


class MerchantAdapter(Protocol):
    """Protocol every adapter implements."""

    def open_session(self, scenario_id: str, seed: int) -> None:
        """Begin a fresh conversation/session."""
        ...

    def send(self, utterance: str) -> MerchantTurn:
        """Send a shopper utterance / action, return the merchant's response."""
        ...

    def close_session(self) -> None:
        ...
