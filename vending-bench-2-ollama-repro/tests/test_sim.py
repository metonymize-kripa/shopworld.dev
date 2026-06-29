from vb2_local.agent import parse_json_tool_call
from vb2_local.runner import run_one
from vb2_local.sim import SimConfig, VendingBench2LocalSim


def test_parse_json_tool_call():
    call = parse_json_tool_call('{"tool":"wait_for_next_day","arguments":{}}')
    assert call.name == "wait_for_next_day"
    assert call.arguments == {}


def test_basic_order_delivery_stock_sale_cycle():
    sim = VendingBench2LocalSim(SimConfig(seed=123, max_days=20))
    result = sim.call_tool(
        "place_order",
        {
            "supplier_email": "sales@bunchvending.example",
            "items": {"Coca-Cola 12oz can": 80, "Bottled Water 16.9oz": 80},
            "max_total": 140,
            "note": "bulk wholesale discount",
        },
    )
    assert result.ok, result.message
    for _ in range(5):
        sim.call_tool("wait_for_next_day", {})
    assert sim.storage["Coca-Cola 12oz can"].qty > 0
    sim.call_tool("stock_machine", {"items": {"Coca-Cola 12oz can": 24, "Bottled Water 16.9oz": 24}})
    sim.call_tool("set_prices", {"prices": {"Coca-Cola 12oz can": 2.75, "Bottled Water 16.9oz": 2.50}})
    before_units = sim.units_sold
    sim.call_tool("wait_for_next_day", {})
    assert sim.units_sold >= before_units
    assert sim.score()["final_balance"] >= 0


def test_scripted_baseline_is_deterministic(tmp_path):
    kwargs = dict(
        model="unused",
        seed=7,
        days=30,
        max_steps=120,
        out_dir=tmp_path,
        scripted_baseline=True,
    )
    a = run_one(**kwargs)
    b = run_one(**kwargs)
    assert a["score"]["final_balance"] == b["score"]["final_balance"]
    assert a["score"]["units_sold"] == b["score"]["units_sold"]
