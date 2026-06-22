"""Tests for the comparative failure-taxonomy report (README §9, §13)."""

from shopworld.agents import BaselineAgent
from shopworld.bench import run_benchmark
from shopworld.bench.compare import summarize, failure_taxonomy, build_markdown
from shopworld.tasks import mvp_task_set

from milli_run import MilliRunAgent
from llm_agent import LLMAgent


def _bench():
    tasks = mvp_task_set()
    factories = {"baseline": BaselineAgent, "milli_run": MilliRunAgent, "llm_agent": LLMAgent}
    return run_benchmark(tasks, factories, seeds=[1])


def test_summary_orders_agents_by_capability():
    bench = _bench()
    summ = summarize(bench)
    assert summ["milli_run"]["success_rate"] >= summ["llm_agent"]["success_rate"]
    assert summ["llm_agent"]["success_rate"] >= summ["baseline"]["success_rate"]
    assert summ["milli_run"]["collateral_damage"] == 0


def test_failure_taxonomy_separates_agents():
    bench = _bench()
    taxo = failure_taxonomy(bench)
    # LLM failures should land in the LLM taxonomy (policy_drift on escalation).
    assert "llm_agent" in taxo
    assert "policy_drift" in taxo["llm_agent"]
    # milli.run should have no failures on the MVP set.
    assert taxo.get("milli_run", {}) == {}


def test_build_markdown_contains_sections():
    bench = _bench()
    md = build_markdown(bench, nlu_section="## NLU benchmark (milli.run)\n\n- stub\n")
    assert "# ShopWorld Comparative Benchmark Report" in md
    assert "Failure taxonomy" in md
    assert "NLU benchmark" in md
