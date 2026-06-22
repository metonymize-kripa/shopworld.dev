"""Tests for the neutral benchmark runner (README §7, §13 interface equality)."""

from shopworld.agents import BaselineAgent, NoOpAgent
from shopworld.bench import run_episode, run_benchmark
from shopworld.tasks import create_wismo_task, create_cancellation_task


def test_run_episode_baseline_resolves_wismo():
    task = create_wismo_task(customer_type="cooperative", days_delayed=10, seed=42)
    result = run_episode(task, BaselineAgent(), seed=1)
    assert result.agent == "baseline"
    assert result.error is None
    # Baseline replies to the ticket -> support_messages success condition met.
    assert result.steps >= 1
    assert result.success is True


def test_noop_agent_fails_gracefully():
    task = create_wismo_task(seed=42)
    result = run_episode(task, NoOpAgent(), seed=1)
    assert result.error is None
    assert result.steps == 0
    assert result.success is False  # did nothing


def test_run_benchmark_matrix():
    tasks = [
        create_wismo_task(seed=42),
        create_cancellation_task(fulfillment_state="UNFULFILLED", seed=42),
    ]
    factories = {"baseline": BaselineAgent, "noop": NoOpAgent}
    bench = run_benchmark(tasks, factories, seeds=[1, 2])
    # 2 tasks x 2 seeds x 2 agents = 8 episodes
    assert len(bench.episodes) == 8
    assert set(bench.agents()) == {"baseline", "noop"}
    # Same scenario+seed handed to both agents (interface equality).
    assert len(bench.by_agent("baseline")) == 4


def test_runner_is_agent_blind():
    """The runner module must not import any agent-under-test."""
    import shopworld.bench.runner as runner_mod
    import inspect

    src = inspect.getsource(runner_mod)
    assert "milli_run" not in src
    assert "llm_agent" not in src
