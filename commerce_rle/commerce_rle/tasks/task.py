"""
Task definition.

A Task bundles everything the env needs to set up, run, and grade one episode:

  - instruction   : natural-language goal shown to the agent
  - seed_rows     : initial DB contents (dict of table -> value tuples)
  - context       : structured facts the agent is allowed to know up front
                    (e.g. its own user_id), mirroring AppWorld's Supervisor app
  - build_tests   : fn(start_state) -> list[Test], the state-diff grader
  - write_scope   : tables a correct solution may mutate; anything else is
                    collateral damage

Generators (see generators.py) produce Tasks parametrically so you get a train
distribution, not one hand-written example.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any

from commerce_rle.env.evaluator import Test, State


@dataclass
class Task:
    task_id: str
    instruction: str
    seed_rows: dict[str, list[tuple]]
    context: dict[str, Any]
    build_tests: Callable[[State], list[Test]]
    write_scope: set[str] = field(default_factory=set)
    # ground-truth answer for answer-seeking tasks (None for action tasks)
    answer: Any = None
    # scenario grouping for Scenario Goal Completion (SGC). Tasks that share a
    # scenario_id are variants of the same goal under different requirements /
    # start states; a scenario is "solved" only if every variant passes.
    scenario_id: str | None = None
    # refusal tasks: the correct behavior is to NOT mutate the DB (item out of
    # stock, over budget, etc.). For these, an empty delta is success. The
    # evaluator rewards "nothing changed + guard tests intact" instead of the
    # usual no_op_fail work fraction (which would be 0/0 on a no-action task).
    expects_refusal: bool = False
