"""Audit layer: record reasoning, guards, reads, writes, escalations (README §7).

The audit trail is milli.run's auditability advantage: every decision is logged
with its cause, so any episode can be explained deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AuditEntry:
    kind: str  # nlu | route | guard | read | write | escalate | reply
    detail: Dict[str, Any]


@dataclass
class AuditLog:
    entries: List[AuditEntry] = field(default_factory=list)

    def record(self, kind: str, **detail: Any) -> None:
        self.entries.append(AuditEntry(kind, detail))

    def to_list(self) -> List[Dict[str, Any]]:
        return [{"kind": e.kind, **e.detail} for e in self.entries]

    def explain(self) -> str:
        lines = []
        for e in self.entries:
            detail = ", ".join(f"{k}={v}" for k, v in e.detail.items())
            lines.append(f"[{e.kind}] {detail}")
        return "\n".join(lines)
