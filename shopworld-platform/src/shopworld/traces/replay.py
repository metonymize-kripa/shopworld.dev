"""Trace action-log extraction and deterministic replay utilities.

These helpers intentionally store only the episode seed and the public action
stream. Replaying the log through ``ShopWorldEnv.step`` verifies that failed
benchmark episodes can be reconstructed without depending on opaque snapshots.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from shopworld.environment import Action, ShopWorldEnv


@dataclass(frozen=True)
class ActionLog:
    """Minimal serializable log needed to replay an episode."""

    seed: Optional[int]
    actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible representation of the action log."""
        return {"seed": self.seed, "actions": list(self.actions)}

    def to_json(self) -> str:
        """Serialize the action log with deterministic key ordering."""
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionLog":
        """Build an action log from a decoded JSON-compatible mapping."""
        return cls(seed=data.get("seed"), actions=list(data.get("actions", [])))

    @classmethod
    def from_json(cls, payload: str) -> "ActionLog":
        """Deserialize a JSON action-log payload."""
        return cls.from_dict(json.loads(payload))


def action_to_dict(action: Action) -> Dict[str, Any]:
    """Convert an ``Action`` into stable, JSON-compatible data."""
    data: Dict[str, Any] = {
        "tool_name": action.tool_name,
        "arguments": dict(action.arguments),
    }
    if action.message is not None:
        data["message"] = action.message
    return data


def action_from_dict(data: Dict[str, Any]) -> Action:
    """Convert serialized action data back into an ``Action`` instance."""
    return Action(
        tool_name=data["tool_name"],
        arguments=dict(data.get("arguments", {})),
        message=data.get("message"),
    )


def extract_action_log(env: ShopWorldEnv) -> ActionLog:
    """Extract the replayable seed and action stream from an environment."""
    return ActionLog(
        seed=env.seed,
        actions=[action_to_dict(step.action) for step in env.get_trace()],
    )


def replay_episode(
    task: Any,
    action_log: ActionLog,
    *,
    max_steps: Optional[int] = None,
    query_cost_budget: int = 10000,
) -> ShopWorldEnv:
    """Replay an action log against a fresh environment and return it."""
    env = ShopWorldEnv(
        task=task,
        max_steps=max_steps,
        query_cost_budget=query_cost_budget,
    )
    env.reset(seed=action_log.seed)
    for action_data in action_log.actions:
        if env.terminated or env.truncated:
            break
        env.step(action_from_dict(action_data))
    return env


def assert_deterministic(task_factory: Callable[[], Any], action_log: ActionLog) -> bool:
    """Return True when replaying the same log twice yields identical state."""
    first = replay_episode(task_factory(), action_log)
    second = replay_episode(task_factory(), action_log)
    return first._get_current_state() == second._get_current_state()
