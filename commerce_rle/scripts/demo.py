"""
Demo: roll the oracle through one of each task type and print the reward signal.

    python scripts/demo.py
"""

from __future__ import annotations
import random

from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.tasks.generators import REGISTRY, sample_task
from commerce_rle.agents import oracle


def main():
    rng = random.Random(7)
    env = CommerceEnv()
    for gen_name in REGISTRY:
        task = sample_task(rng, gen_name)
        obs = env.reset(task)
        tag = " [refusal]" if task.expects_refusal else ""
        print(f"\n=== {gen_name}{tag} ===")
        print(f"  task_id    : {task.task_id}")
        print(f"  instruction: {task.instruction}")
        print(f"  write_scope: {sorted(task.write_scope) or '(none — must not mutate)'}")
        result = oracle.solve(env, obs)
        info = result.info
        print(f"  -> reward            : {result.reward:+.3f}")
        print(f"  -> tgc               : {info['tgc']}")
        print(f"  -> collateral_damage : {info['collateral_damage']}")
        print(f"  -> collateral_fields : {info['collateral_fields']}")
        print(f"  -> steps             : {info['steps']}")
    env.close()


if __name__ == "__main__":
    main()
