"""Regex entity extraction for merchant workflows.

Pulls order ids/numbers, emails, money amounts, and dates out of free text.
milli.run owns entity extraction (README §7).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ORDER_NUM_RE = re.compile(r"#\s?(\d{3,})")
_ORDER_ID_RE = re.compile(r"\border[-_ ]?(\d{1,})\b", re.IGNORECASE)
_GID_RE = re.compile(r"gid://shopify/Order/\w+")
_MONEY_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


@dataclass
class Entities:
    emails: List[str] = field(default_factory=list)
    order_numbers: List[str] = field(default_factory=list)
    order_ids: List[str] = field(default_factory=list)
    amounts: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)

    @property
    def order_ref(self) -> Optional[str]:
        if self.order_ids:
            return self.order_ids[0]
        if self.order_numbers:
            return self.order_numbers[0]
        return None


class EntityExtractor:
    def extract(self, text: str) -> Entities:
        text = text or ""
        return Entities(
            emails=_EMAIL_RE.findall(text),
            order_numbers=[m.group(1) for m in _ORDER_NUM_RE.finditer(text)],
            order_ids=_GID_RE.findall(text) + [m.group(0) for m in _ORDER_ID_RE.finditer(text)],
            amounts=[float(m.group(1)) for m in _MONEY_RE.finditer(text)],
            dates=_DATE_RE.findall(text),
        )
