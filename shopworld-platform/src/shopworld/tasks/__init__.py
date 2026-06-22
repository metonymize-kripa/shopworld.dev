"""Built-in task library for ShopWorld.

MVP scenario families (README §10):
  - WISMO
  - Cancellation
  - Address change
  - Refund
  - Return
"""

from typing import List

from shopworld.task import Task
from shopworld.tasks.wismo import create_wismo_task
from shopworld.tasks.cancellation import create_cancellation_task
from shopworld.tasks.address_change import create_address_change_task
from shopworld.tasks.refund import create_refund_task
from shopworld.tasks.return_item import create_return_task
from shopworld.tasks.escalation import create_escalation_task

__all__ = [
    "create_wismo_task",
    "create_cancellation_task",
    "create_address_change_task",
    "create_refund_task",
    "create_return_task",
    "create_escalation_task",
    "mvp_task_set",
]


def mvp_task_set(seed: int = 42) -> List[Task]:
    """The MVP scenario set: 6 families x 5 state-dependent variants = 30
    grounded scenarios (README §10).

    Each variant encodes a different correct behavior for the same surface
    request, which is the point of the benchmark (same utterance, different
    store state => different right action).
    """
    return [
        # --- WISMO (5): temperament + delay variants ---------------------
        create_wismo_task(customer_type="cooperative", days_delayed=10, seed=seed),
        create_wismo_task(customer_type="angry", days_delayed=14, seed=seed),
        create_wismo_task(customer_type="vip", days_delayed=7, seed=seed),
        create_wismo_task(customer_type="cooperative", days_delayed=21, seed=seed + 1),
        create_wismo_task(customer_type="angry", days_delayed=30, seed=seed + 2),
        # --- Cancellation (5): cancellable vs must-block ------------------
        create_cancellation_task(fulfillment_state="UNFULFILLED", seed=seed),
        create_cancellation_task(fulfillment_state="FULFILLED", seed=seed),
        create_cancellation_task(fulfillment_state="UNFULFILLED", seed=seed + 1),
        create_cancellation_task(fulfillment_state="FULFILLED", seed=seed + 2),
        create_cancellation_task(fulfillment_state="UNFULFILLED", seed=seed + 3),
        # --- Address change (5): intercept feasibility -------------------
        create_address_change_task(fulfillment_state="UNFULFILLED", label_created=False, seed=seed),
        create_address_change_task(fulfillment_state="UNFULFILLED", label_created=True, seed=seed),
        create_address_change_task(fulfillment_state="FULFILLED", label_created=True, seed=seed),
        create_address_change_task(fulfillment_state="UNFULFILLED", label_created=False, seed=seed + 1),
        create_address_change_task(fulfillment_state="FULFILLED", label_created=True, seed=seed + 2),
        # --- Refund (5): in-window / out-of-window / fraud ---------------
        create_refund_task(days_since_delivery=3, fraud_risk=0.1, seed=seed),
        create_refund_task(days_since_delivery=60, fraud_risk=0.1, seed=seed),
        create_refund_task(days_since_delivery=3, fraud_risk=0.9, seed=seed),
        create_refund_task(days_since_delivery=10, fraud_risk=0.5, seed=seed + 1),
        create_refund_task(days_since_delivery=45, fraud_risk=0.2, seed=seed + 2),
        # --- Return (5): returnable / out-of-window / final-sale ---------
        create_return_task(days_since_delivery=7, is_final_sale=False, seed=seed),
        create_return_task(days_since_delivery=60, is_final_sale=False, seed=seed),
        create_return_task(days_since_delivery=7, is_final_sale=True, seed=seed),
        create_return_task(days_since_delivery=20, is_final_sale=False, seed=seed + 1),
        create_return_task(days_since_delivery=10, is_final_sale=True, seed=seed + 2),
        # --- Escalation (5): abuse/threat must be escalated --------------
        create_escalation_task(variant="legal_threat", seed=seed),
        create_escalation_task(variant="chargeback_threat", seed=seed),
        create_escalation_task(variant="fraud_accusation", seed=seed),
        create_escalation_task(variant="legal_threat", seed=seed + 1),
        create_escalation_task(variant="chargeback_threat", seed=seed + 2),
    ]
