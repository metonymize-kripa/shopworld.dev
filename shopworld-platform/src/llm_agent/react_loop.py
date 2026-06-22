"""ReAct-style helpers: build prompts and parse LLM tool-call output."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROMPT_DIR = Path(__file__).parent / "prompts"
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def load_system_prompt() -> str:
    parts = []
    for name in ("merchant_system.md", "policy_context.md"):
        path = _PROMPT_DIR / name
        if path.exists():
            parts.append(path.read_text())
    return "\n\n".join(parts)


def build_user_message(
    ticket: Dict[str, Any], order: Optional[Dict[str, Any]], history: List[str]
) -> str:
    """Human-readable turn plus a machine-readable CONTEXT block.

    A real model reads the prose; the offline ScriptedLLMClient reads CONTEXT.
    """
    context = {
        "ticket_id": ticket.get("id"),
        "order_id": ticket.get("order_id"),
        "subject": ticket.get("subject"),
        "description": ticket.get("description"),
        "order": order,
        "history": history,
    }
    prose = (
        f"Support ticket {ticket.get('id')}: \"{ticket.get('subject')}\"\n"
        f"Customer message: {ticket.get('description')}\n"
        f"Order on file: {order if order else 'none found'}\n"
        f"Tools already called this ticket: {history or 'none'}\n"
        "Decide the single next tool call."
    )
    return prose + f"\n<CONTEXT>{json.dumps(context)}</CONTEXT>"


def parse_action(text: str) -> Optional[Dict[str, Any]]:
    """Extract a {'tool':..., 'args':...} object from an LLM response."""
    if not text:
        return None
    match = _JSON_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if "tool" not in data:
        return None
    data.setdefault("args", {})
    return data
