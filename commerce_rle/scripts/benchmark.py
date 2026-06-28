"""
Benchmark a policy with AppWorld's metrics: TGC, SGC, sub-goal completion.

    python scripts/benchmark.py

Runs the oracle (swap in your policy) over a scenario-grouped dataset and reports
the same numbers you'd put on the AppWorld leaderboard:

  TGC  — Task Goal Completion: % of tasks where ALL unit tests pass.
  SGC  — Scenario Goal Completion: % of scenarios where ALL variant tasks pass.
  SubG — Sub-Goal Completion: mean fraction of unit tests passed (partial credit).
"""

from __future__ import annotations
from collections import defaultdict

from commerce_rle.env.commerce_env import CommerceEnv
from commerce_rle.env.evaluator import (
    evaluate, snapshot, scenario_goal_completion, aggregate_metrics,
)
from commerce_rle.tasks.generators import make_scenarios
from commerce_rle.agents import oracle


def run_policy(env: CommerceEnv, task, policy=oracle.solve):
    """Run one task to completion, return its final Evaluation."""
    obs = env.reset(task)
    policy(env, obs)
    # grade the final state once more, independent of reward mode
    end = snapshot(env.conn)
    return evaluate(env.tests, env.start_state, end,
                    write_scope=task.write_scope)


def main(scenarios_per_family: int = 2, variants: int = 3, seed: int = 0):
    # stratified: guarantee every task family is represented, so coverage is
    # deterministic rather than left to random allocation.
    from commerce_rle.tasks.generators import make_stratified_scenarios
    tasks = make_stratified_scenarios(
        variants_per_scenario=variants,
        scenarios_per_family=scenarios_per_family, seed=seed,
    )
    # AppWorld's native metric is binary, so reward_mode doesn't affect grading
    # here — we evaluate the end state directly. Use "appworld" for clarity.
    env = CommerceEnv(reward_mode="appworld")

    by_scenario: dict[str, list] = defaultdict(list)
    all_evals = []
    for task in tasks:
        ev = run_policy(env, task)
        by_scenario[task.scenario_id].append(ev)
        all_evals.append(ev)
    env.close()

    task_metrics = aggregate_metrics(all_evals)
    sgc_per_scenario = [
        scenario_goal_completion(evs) for evs in by_scenario.values()
    ]
    sgc = sum(sgc_per_scenario) / len(sgc_per_scenario) if sgc_per_scenario else 0.0

    print("=== AppWorld-style benchmark (oracle policy) ===")
    print(f"  tasks                 : {task_metrics['n']}")
    print(f"  scenarios             : {len(by_scenario)} (x{variants} variants)")
    print(f"  TGC  (task goal)      : {task_metrics['tgc']:.3f}")
    print(f"  SGC  (scenario goal)  : {sgc:.3f}")
    print(f"  SubG (partial credit) : {task_metrics['sub_goal_completion']:.3f}")

    # coverage: how many scenarios drew from each generator family
    from collections import Counter
    fam = Counter(sid.split("__scenario_")[0] for sid in by_scenario)
    print("\n  scenario coverage by task family:")
    for name in sorted(fam):
        tag = " (refusal)" if name in __import__(
            "commerce_rle.tasks.generators", fromlist=["REFUSAL_GENERATORS"]
        ).REFUSAL_GENERATORS else ""
        print(f"    {name:28} {fam[name]} scenario(s){tag}")
    print()
    print("  Note: oracle should score 1.000 across the board. A trained policy's")
    print("  gap below these numbers is its true error rate on this distribution.")


if __name__ == "__main__":
    main()
