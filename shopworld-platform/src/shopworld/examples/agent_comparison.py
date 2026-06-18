"""Compare bad, mediocre, and excellent agents on the same WISMO task.

Run with:
    uv run shopworld compare-agents
"""

from shopworld.environment import ShopWorldEnv, Action
from shopworld.tasks.wismo import create_wismo_task


def create_task():
    return create_wismo_task(customer_type="cooperative", days_delayed=10, seed=42)


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

def bad_agent_episode(env):
    """Bad agent: ignores the ticket, tries forbidden actions, wastes budget."""
    actions = [
        # Tries to adjust inventory — scope violation, blocked
        Action(tool_name="adjust_inventory",
               arguments={"inventory_item_id": "x", "location_id": "y", "delta": 5}),
        # Tries again — another violation
        Action(tool_name="adjust_inventory",
               arguments={"inventory_item_id": "x", "location_id": "y", "delta": -3}),
        # Redundant reads that don't relate to the ticket
        Action(tool_name="query_orders", arguments={"first": 50}),
        Action(tool_name="query_orders", arguments={"first": 50}),
        Action(tool_name="query_orders", arguments={"first": 50}),
        # Never sends a message — task will fail
    ]
    return _run_actions(env, actions)


def mediocre_agent_episode(env):
    """Mediocre agent: completes the task, but wastes steps and sends a vague reply."""
    actions = [
        # Reads orders (fine, but overly broad)
        Action(tool_name="query_orders", arguments={"first": 50}),
        # Reads orders again — wasteful duplicate
        Action(tool_name="query_orders", arguments={"first": 50}),
        # Reads tickets
        Action(tool_name="query_support_tickets", arguments={"status": "OPEN"}),
        # Another redundant read
        Action(tool_name="query_orders", arguments={"first": 10}),
        # Finally replies — but generic and unhelpful
        Action(tool_name="send_message", arguments={
            "ticket_id": "ticket-wismo-001",
            "message": "We are looking into this. Please wait.",
        }),
    ]
    return _run_actions(env, actions)


def excellent_agent_episode(env):
    """Excellent agent: targeted reads, personalized reply, closes the ticket."""
    actions = [
        # Step 1: Read open tickets to understand the problem
        Action(tool_name="query_support_tickets", arguments={"status": "OPEN"}),
        # Step 2: Look up the specific order tied to the ticket
        Action(tool_name="query_orders", arguments={"first": 10}),
        # Step 3: Close the ticket (before reply, since reply triggers terminal)
        Action(tool_name="close_ticket", arguments={
            "ticket_id": "ticket-wismo-001",
        }),
        # Step 4: Send a personalized, informative reply (triggers episode end)
        Action(tool_name="send_message", arguments={
            "ticket_id": "ticket-wismo-001",
            "message": (
                "Hi! I've checked on your order and I can see it's currently "
                "being processed for shipment. I understand the delay is "
                "frustrating — your tracking number is 1Z999888777666 via UPS. "
                "You should see movement within 24-48 hours. I'll keep an eye "
                "on it and follow up if anything changes. Thank you for your patience!"
            ),
        }),
    ]
    return _run_actions(env, actions)


# ---------------------------------------------------------------------------
# Runner helpers
# ---------------------------------------------------------------------------

def _run_actions(env, actions):
    """Execute a list of actions and return (steps_taken, result)."""
    steps = []
    for action in actions:
        obs, reward, terminated, truncated, info = env.step(action)
        steps.append({
            "tool": action.tool_name,
            "violations": info["violations"],
            "cost_remaining": obs.query_cost_remaining,
        })
        if terminated or truncated:
            break
    result = env.evaluate()
    return steps, result


def _print_header(label, emoji):
    print(f"\n{'─' * 60}")
    print(f"  {emoji}  {label}")
    print(f"{'─' * 60}")


def _print_steps(steps):
    for i, s in enumerate(steps, 1):
        violation_tag = ""
        if s["violations"]:
            violation_tag = f"  ⛔ {', '.join(s['violations'])}"
        print(f"   {i}. {s['tool']:<28} cost remaining: {s['cost_remaining']}{violation_tag}")


def _print_result(result):
    task = result.get("task", {})
    safety = result.get("safety", {})
    violations = safety.get("violations", {})
    overall = result.get("overall", {})

    success = task.get("success", False)
    score = overall.get("score", 0)
    rec = overall.get("recommendation", "N/A")
    passed = len(task.get("passed", []))
    failed = len(task.get("failed", []))
    scope_v = violations.get("scope", 0)

    print(f"\n   Task success:       {'✅ YES' if success else '❌ NO'}")
    print(f"   Completion:         {task.get('completion_score', 0)*100:.0f}%  "
          f"({passed} passed, {failed} failed)")
    if scope_v > 0:
        print(f"   Scope violations:   ⚠️  {scope_v}")
    print(f"   Overall score:      {score:.1f} / 100")
    print(f"   Recommendation:     {rec.upper()}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  ShopWorld Agent Comparison — WISMO Scenario")
    print("=" * 60)
    print()
    print("Same task, three agents, very different outcomes.")
    print("Task: Cooperative customer, order delayed 10 days.")

    agents = [
        ("Bad Agent",       "🔴", bad_agent_episode),
        ("Mediocre Agent",  "🟡", mediocre_agent_episode),
        ("Excellent Agent", "🟢", excellent_agent_episode),
    ]

    for label, emoji, agent_fn in agents:
        task = create_task()
        env = ShopWorldEnv(task=task, enable_tracing=True, max_steps=15)
        env.reset(seed=42)

        _print_header(label, emoji)
        steps, result = agent_fn(env)

        print("\n   Actions taken:")
        _print_steps(steps)
        _print_result(result)

    print(f"\n{'=' * 60}")
    print("  Key takeaways:")
    print("  • Scope violations → safety penalty, lower score")
    print("  • Redundant queries → wasted API budget")
    print("  • Targeted actions + helpful reply → high score")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
