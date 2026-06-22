"""Neutral agent contract for the benchmark harness.

This package defines only the *interface* every evaluated agent implements plus
trivial neutral baselines. It contains no milli.run or LLM logic, so ShopWorld
core never imports an agent-under-test (README §13 environment separation).
"""

from shopworld.agents.base import Agent, BaselineAgent, NoOpAgent

__all__ = ["Agent", "BaselineAgent", "NoOpAgent"]
