"""Minimal example: Create a ShopWorld environment and run a WISMO task."""

from shopworld.environment import ShopWorldEnv, Action
from shopworld.tasks.wismo import create_wismo_task


def create_sample_task():
    """Create a WISMO (Where Is My Order) support task."""
    return create_wismo_task(
        customer_type="cooperative",
        days_delayed=10,
        seed=42,
    )


def dummy_agent(observation) -> Action:
    """Dummy agent that just queries inventory."""
    # In a real agent, this would use LLM/tool-calling
    return Action(
        tool_name="query_inventory",
        arguments={"location_id": "main"},
    )


def main():
    """Run a ShopWorld WISMO episode."""
    print("=" * 60)
    print("ShopWorld: WISMO (Where Is My Order) Support Scenario")
    print("=" * 60)
    
    # Create WISMO task
    task = create_sample_task()
    print(f"\n📋 Task: {task.name}")
    print(f"   {task.description}")
    print(f"   Difficulty: {task.difficulty}/3 | Domain: {task.domain}")
    print(f"   Allowed scopes: {', '.join(task.allowed_scopes)}")
    
    # Show scenario setup
    print("\n📦 Initial Store State:")
    print(f"   Products: {len(task.initial_db_records.get('products', []))}")
    print(f"   Customers: {len(task.initial_db_records.get('customers', []))}")
    print(f"   Orders: {len(task.initial_db_records.get('orders', []))}")
    print(f"   Support Tickets: {len(task.initial_db_records.get('support_tickets', []))}")
    
    # Show active ticket
    tickets = task.initial_db_records.get('support_tickets', [])
    if tickets:
        ticket = tickets[0]
        print(f"\n🎫 Active Support Ticket:")
        print(f"   Subject: {ticket['subject']}")
        print(f"   Priority: {ticket['priority']}")
        print(f"   Description: {ticket['description'][:80]}...")
    
    # Create environment
    env = ShopWorldEnv(
        task=task,
        enable_tracing=True,
        max_steps=15,
    )
    
    # Reset environment
    print("\n[Initializing environment...]")
    obs, info = env.reset(seed=42)
    print(f"✅ Episode ID: {info['episode_id']}")
    print(f"   Granted scopes: {', '.join(info['granted_scopes'])}")
    print(f"   Simulated time: {obs.timestamp}")
    
    # Run episode with simple agent
    print("\n🤖 Running agent episode (dummy agent)...")
    done = False
    step = 0
    
    while not done and step < 5:  # Limit for demo
        # Simple agent: query orders then query support tickets
        if step == 0:
            action = Action(tool_name="query_orders", arguments={"first": 10})
        elif step == 1:
            action = Action(tool_name="query_support_tickets", arguments={"status": "OPEN"})
        else:
            action = Action(tool_name="send_message", arguments={
                "ticket_id": "ticket-wismo-001",
                "message": "I'm looking into your order now. Let me check the tracking information."
            })
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        print(f"\n   Step {obs.step_number}: {action.tool_name}")
        print(f"   API cost: {obs.query_cost_remaining} remaining")
        
        done = terminated or truncated
        step += 1
    
    # Evaluate
    print("\n[Evaluating episode...]")
    result = env.evaluate()
    
    task_result = result.get('task_completion', {})
    print(f"\n📊 Results:")
    print(f"   Task success: {'✅ YES' if task_result.get('success') else '❌ NO'}")
    print(f"   Completion score: {task_result.get('partial_credit', 0)*100:.0f}%")
    print(f"   Passed checks: {len(task_result.get('passed_checks', []))}")
    print(f"   Failed checks: {len(task_result.get('failed_checks', []))}")
    
    violations = result.get('policy_violations', {})
    if violations.get('total', 0) > 0:
        print(f"   ⚠️  Policy violations: {violations['total']}")
    
    print("\n" + "=" * 60)
    print("Episode complete!")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    main()
