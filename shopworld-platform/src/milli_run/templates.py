"""Controlled customer-facing response templates (README §7)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def wismo(order: Optional[Dict[str, Any]]) -> str:
    name = order.get("name") if order else "your order"
    return (
        f"Thanks for checking in on {name}. I've pulled up your order and the latest "
        "shipment tracking. It's in transit and running behind the original estimate; "
        "I've flagged it with the carrier and will keep you posted."
    )


def cancel_confirmed(order: Optional[Dict[str, Any]]) -> str:
    name = order.get("name") if order else "your order"
    return f"Your order {name} has been cancelled and the charge voided. You'll see the funds released shortly."


def cancel_blocked(order: Optional[Dict[str, Any]]) -> str:
    name = order.get("name") if order else "your order"
    return (
        f"I'm sorry, but {name} has already been fulfilled and shipped, so it can no longer "
        "be cancelled. Once it arrives you can start a return and we'll refund it."
    )


def address_change_confirmed() -> str:
    return (
        "I've updated the shipping address on your order before it ships. "
        "Please double-check the new address in your confirmation."
    )


def address_change_blocked() -> str:
    return (
        "Your order has already shipped, so I can't change the delivery address here. "
        "I've escalated to our team to attempt a carrier intercept."
    )


def refund_confirmed(order: Optional[Dict[str, Any]]) -> str:
    return (
        "I've processed your refund to the original payment method. "
        "It typically takes 3-5 business days to appear."
    )


def refund_blocked(reason: str) -> str:
    return (
        "I wasn't able to process a refund automatically, so I've escalated your request "
        "to our support team for a closer look. They'll follow up shortly."
    )


def return_started() -> str:
    return (
        "I've started a return for your order. You'll receive a prepaid label and "
        "instructions by email — just pack the item and drop it off."
    )


def return_blocked() -> str:
    return (
        "I'm sorry, but this item isn't eligible for return right now. I've escalated "
        "your request so our team can review the specifics with you."
    )


def escalation(reason: str) -> str:
    return (
        "Thanks for your patience — I've routed your request to a specialist on our team "
        "who can help with this. They'll reach out shortly."
    )
