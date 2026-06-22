"""Neutral benchmark harness (README §7 'Benchmark runner owns').

The runner executes the same loop for every agent and never gives one agent more
privileged information than another. It imports ShopWorld and the agent *protocol*
only — never a specific agent implementation.
"""

from shopworld.bench.runner import (
    EpisodeResult,
    BenchmarkResult,
    run_episode,
    run_benchmark,
)

__all__ = ["EpisodeResult", "BenchmarkResult", "run_episode", "run_benchmark"]
