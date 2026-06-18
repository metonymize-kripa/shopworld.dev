# Example 1: WISMO (Where Is My Order) Support Scenario

This example demonstrates running a complete ShopWorld episode for a customer support scenario.

## Scenario Overview

**Task**: A customer has placed an order 10+ days ago and is asking "Where is my order?"

**Agent Goal**: 
1. Look up the customer's order
2. Check fulfillment status
3. Find tracking information
4. Send appropriate response to the customer

**Authority Level**: Supervised (read + limited write access)

---

## Step 1: Run the Scenario

```bash
cd /Users/kripar/Documents/coding/shopworld.dev/shopworld-platform
uv run shopworld hello
```

**Output:**
```
============================================================
ShopWorld: WISMO (Where Is My Order) Support Scenario
============================================================

📋 Task: WISMO - Cooperative customer, 10 days delayed
   A cooperative customer is asking about their order placed 10 days ago. 
   Find the order, check status, and provide appropriate response.
   Difficulty: 1/3 | Domain: support
   Allowed scopes: read_orders, read_customers, read_fulfillments, write_orders

📦 Initial Store State:
   Products: 10
   Customers: 50
   Orders: 100
   Support Tickets: 12

🎫 Active Support Ticket:
   Subject: Where is my order?
   Priority: MEDIUM
   Description: I placed this order 14 days ago and haven't received it ye...
```

---

## Step 2: Environment Initialization

When the environment resets, it:
- Creates an in-memory SQLite database
- Seeds it with store data (products, customers, orders, tickets)
- Starts the simulated clock at 2024-01-01
- Grants the agent specific API scopes

```
[Initializing environment...]
✅ Episode ID: be5e1b4f
   Granted scopes: read_orders, read_customers, read_fulfillments, write_orders
   Simulated time: 2024-01-01 00:00:00
```

---

## Step 3: Agent Episode Execution

The dummy agent performs these actions:

### Action 1: Query Orders
```python
Action(tool_name="query_orders", arguments={"first": 10})
```

**Result:** API cost remaining: 9990

### Action 2: Query Support Tickets
```python
Action(tool_name="query_support_tickets", arguments={"status": "OPEN"})
```

**Result:** API cost remaining: 9980

### Action 3-5: Send Messages
```python
Action(tool_name="send_message", arguments={
    "ticket_id": "ticket-wismo-001",
    "message": "I'm looking into your order now..."
})
```

**Result:** API cost decrements by 10 per action

---

## Step 4: Episode Evaluation

```
[Evaluating episode...]

📊 Results:
   Task success: ❌ NO
   Completion score: 0%
   Passed checks: 0
   Failed checks: 2
```

**Why it failed:**
- The dummy agent didn't actually complete the required checks
- Missing: Verified order lookup against ticket
- Missing: Provided specific tracking information

---

## Understanding the Data Model

### Generated Store Data
```
Products: 10 products with ~3-6 variants each
Customers: 50 customers with realistic profiles  
Orders: 100 orders (mix of fulfilled/unfulfilled/partial)
Tickets: 12 support tickets (mix of open/closed)
```

### Database Tables Created
```bash
uv run shopworld schema
```

**Output:**
```
ShopWorld Database Schema
┌──────────────┬─────────────────────────────────────────────────────────────┐
│ Table        │ Columns                                                     │
├──────────────┼─────────────────────────────────────────────────────────────┤
│ products     │ id, title, handle, description, product_type, vendor, ... │
│ product_var  │ id, product_id, sku, option1, option2, price, cost, ...   │
│ orders       │ id, name, customer_id, display_financial_status, ...       │
│ order_line_  │ id, order_id, product_id, variant_id, quantity, price, ... │
│ customers    │ id, email, first_name, last_name, orders_count, ...      │
│ inventory_l  │ id, inventory_item_id, location_id, available, ...       │
│ support_tic  │ id, customer_id, order_id, subject, status, priority, ...  │
└──────────────┴─────────────────────────────────────────────────────────────┘
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

**Output:**
```
============================= test session starts ==============================
platform darwin -- Python 3.12.9, pytest-9.1.0
rootdir: /Users/kripar/Documents/coding/shopworld.dev/shopworld-platform

src/shopworld/tests/test_environment.py::test_environment_init PASSED   [  5%]
src/shopworld/tests/test_environment.py::test_environment_reset PASSED  [ 10%]
src/shopworld/tests/test_environment.py::test_environment_step PASSED   [ 15%]
src/shopworld/tests/test_environment.py::test_environment_termination PASSED [ 20%]
src/shopworld/tests/test_environment.py::test_trace_recording PASSED    [ 25%]
src/shopworld/tests/test_models.py::TestProductModel::test_create_product PASSED [ 30%]
src/shopworld/tests/test_models.py::TestOrderModel::test_create_order PASSED [ 35%]
src/shopworld/tests/test_models.py::TestOrderModel::test_order_line_items PASSED [ 40%]
src/shopworld/tests/test_models.py::TestInventoryModel::test_inventory_levels PASSED [ 45%]
src/shopworld/tests/test_models.py::TestSupportTicketModel::test_create_ticket PASSED [ 50%]
src/shopworld/tests/test_models.py::TestCustomerModel::test_create_customer PASSED [ 55%]
...

======================== 19 passed, 15 warnings =============================
```

---

## Programmatic Usage

```python
from shopworld.environment import ShopWorldEnv, Action
from shopworld.tasks.wismo import create_wismo_task

# Create task with specific parameters
task = create_wismo_task(
    customer_type="vip",  # or "cooperative", "angry", "opportunistic"
    days_delayed=14,
    seed=42
)

# Initialize environment
env = ShopWorldEnv(task=task, max_steps=20)
obs, info = env.reset(seed=42)

# Agent loop
done = False
while not done:
    # Your agent logic here
    action = Action(tool_name="query_orders", arguments={})
    
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

# Evaluate results
result = env.evaluate()
print(f"Success: {result['task_completion']['success']}")
print(f"Score: {result['task_completion']['partial_credit']}")
```

---

## Task Success Conditions

For this WISMO task to pass, the agent must:

1. ✅ Query the support ticket to understand the issue
2. ✅ Find the associated order by order_id or customer lookup
3. ✅ Check fulfillment status (unfulfilled/partial/fulfilled)
4. ✅ Look up tracking information if available
5. ✅ Send a helpful response to the customer with specific information

**Authority Constraints:**
- Can read orders, customers, fulfillments
- Can write order notes
- Cannot: cancel orders, issue refunds, modify inventory

---

## Reward Components

Each step produces a multi-dimensional reward vector:

```python
{
    "task_completion": 0.0,      # Progress toward goal
    "business_outcome": 0.0,     # Revenue/margin impact
    "customer_outcome": 0.0,     # Satisfaction change
    "operational_outcome": 0.0,  # SLA compliance
    "api_efficiency": -0.005,    # API cost penalty
    "query_correctness": 0.0,    # Valid queries
    "policy_compliance": 0.0,    # Scope adherence
    "collateral_damage": 0.0,    # Unintended changes
}
```

---

## Next Steps

1. **Build a real agent** that uses LLM to decide actions
2. **Add more scenarios** like inventory restocking or refund processing
3. **Connect to customer simulator** for dynamic ticket generation
4. **Run benchmarks** across multiple task variants

See `IMPLEMENTATION_STATUS.md` for full project status.
