"""Policy guards: prevent invalid writes before they reach the API surface.

Guards reason over *observable* order state (the same fields any agent can see).
They encode the merchant policy constraints milli.run owns (README §7: prevents
invalid refunds, cancellations, discounts, and address changes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class GuardResult:
    allowed: bool
    reason: str


class PolicyGuards:
    def cancel(self, order: Optional[Dict[str, Any]]) -> GuardResult:
        if not order:
            return GuardResult(False, "order_not_found")
        if order.get("display_fulfillment_status") == "FULFILLED":
            return GuardResult(False, "already_fulfilled")
        if order.get("display_financial_status") == "VOIDED":
            return GuardResult(False, "already_cancelled")
        return GuardResult(True, "cancellable_before_fulfillment")

    def refund(self, order: Optional[Dict[str, Any]], amount: float) -> GuardResult:
        if not order:
            return GuardResult(False, "order_not_found")
        total = float(order.get("total_price", 0) or 0)
        if amount <= 0:
            return GuardResult(False, "non_positive_amount")
        if amount > total:
            return GuardResult(False, "amount_exceeds_order_total")
        if order.get("display_financial_status") == "REFUNDED":
            return GuardResult(False, "already_refunded")
        if order.get("display_financial_status") not in ("PAID", "PARTIALLY_REFUNDED"):
            return GuardResult(False, "order_not_paid")
        return GuardResult(True, "within_refundable_value")

    def return_item(self, order: Optional[Dict[str, Any]]) -> GuardResult:
        if not order:
            return GuardResult(False, "order_not_found")
        if order.get("display_fulfillment_status") not in ("FULFILLED", "PARTIAL"):
            return GuardResult(False, "not_yet_delivered")
        return GuardResult(True, "delivered_returnable")

    def address_change(self, order: Optional[Dict[str, Any]]) -> GuardResult:
        if not order:
            return GuardResult(False, "order_not_found")
        if order.get("display_fulfillment_status") in ("FULFILLED", "PARTIAL"):
            return GuardResult(False, "already_shipped")
        return GuardResult(True, "pre_fulfillment_editable")
