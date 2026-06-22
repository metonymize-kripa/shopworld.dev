"""Neutral experiment loop that runs agents against identical scenarios.

Implements the ten-step loop from README §7:

    1. Load scenario.        2. Reset ShopWorld with scenario seed.
    3. Reset evaluated agent. 4. Provide initial observation + tool schemas.
    5. Receive agent action.  6. Execute action through Merchant API Surface.
    7. Return tool result / updated observation.  8. Continue until termination.
    9. Run evaluator.        10. Save trace.  (11. Compare — see compare.py.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from shopworld.agents.base import Agent
from shopworld.environment import ShopWorldEnv
from shopworld.traces.replay import ActionLog, extract_action_log


@dataclass
class EpisodeResult:
    """Outcome of one (agent, scenario, seed) episode."""

    agent: str
    task_id: str
    seed: int
    steps: int
    terminated: bool
    truncated: bool
    success: bool
    overall_score: float
    recommendation: str
    evaluation: Dict[str, Any]
    action_log: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "task_id": self.task_id,
            "seed": self.seed,
            "steps": self.steps,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "success": self.success,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation,
            "evaluation": self.evaluation,
            "action_log": self.action_log,
            "error": self.error,
        }


@dataclass
class BenchmarkResult:
    """All episodes across agents and scenarios."""

    episodes: List[EpisodeResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"episodes": [e.to_dict() for e in self.episodes]}

    def by_agent(self, agent: str) -> List[EpisodeResult]:
        return [e for e in self.episodes if e.agent == agent]

    def agents(self) -> List[str]:
        seen: List[str] = []
        for e in self.episodes:
            if e.agent not in seen:
                seen.append(e.agent)
        return seen


def run_episode(
    task: Any,
    agent: Agent,
    seed: int = 0,
    max_steps: int = 25,
    query_cost_budget: int = 10000,
) -> EpisodeResult:
    """Run a single agent on a single scenario and evaluate it.

    The runner is neutral: it hands every agent the same observation, executes
    every action through the same env.step (Merchant API Surface), and applies
    the same Evaluator. The agent is a black box behind the Agent protocol.
    """
    env = ShopWorldEnv(task=task, max_steps=max_steps, query_cost_budget=query_cost_budget)
    obs, info = env.reset(seed=seed)

    error: Optional[str] = None
    try:
        agent.reset(obs, info)
        for _ in range(max_steps):
            if env.terminated or env.truncated:
                break
            action = agent.act(obs)
            if action is None:  # agent signals completion
                break
            obs, _reward, terminated, truncated, _info = env.step(action)
            if terminated or truncated:
                break
    except Exception as exc:  # an agent crash is a failed episode, not a runner crash
        error = f"{type(exc).__name__}: {exc}"

    evaluation = env.evaluate()
    action_log: ActionLog = extract_action_log(env)

    return EpisodeResult(
        agent=getattr(agent, "name", agent.__class__.__name__),
        task_id=task.id,
        seed=seed,
        steps=env.step_number,
        terminated=env.terminated,
        truncated=env.truncated,
        success=evaluation.get("task", {}).get("success", False),
        overall_score=evaluation.get("overall", {}).get("score", 0.0),
        recommendation=evaluation.get("overall", {}).get("recommendation", "unknown"),
        evaluation=evaluation,
        action_log={"seed": action_log.seed, "actions": action_log.actions},
        error=error,
    )


def run_benchmark(
    tasks: List[Any],
    agent_factories: Dict[str, Callable[[], Agent]],
    seeds: Optional[List[int]] = None,
    max_steps: int = 25,
) -> BenchmarkResult:
    """Run every agent against every (task, seed) and collect results.

    ``agent_factories`` maps an agent name to a zero-arg constructor so each
    episode gets a fresh agent instance with no cross-episode state leakage.
    """
    seeds = seeds or [0]
    result = BenchmarkResult()
    for task in tasks:
        for seed in seeds:
            for name, factory in agent_factories.items():
                agent = factory()
                episode = run_episode(task, agent, seed=seed, max_steps=max_steps)
                episode.agent = name  # canonical name from the registry
                result.episodes.append(episode)
    return result
