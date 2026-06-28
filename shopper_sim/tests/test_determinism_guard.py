"""Guard tests enforcing determinism discipline.

These assert the *source* of the runtime engine never reaches for a
non-deterministic primitive. In a full project this is a ruff plugin +
import-linter contract; here it's a lightweight source scan so the guarantee is
checked in CI without extra tooling.
"""

from __future__ import annotations

import pathlib
import re

# Packages that are part of the deterministic runtime path. The authoring path
# (graph DB, offline LLM tooling) is exempt but isn't shipped here anyway.
_RUNTIME_PACKAGES = [
    "engine",
    "taxonomy",
    "persona",
    "nlg",
    "adapters",
    "oracle",
    "orchestrator",
    "reporting",
]

_PKG_ROOT = pathlib.Path(__file__).resolve().parents[1] / "shopper_sim"

# Patterns that would break determinism if used in the runtime path.
_BANNED = [
    re.compile(r"^\s*import\s+random\b", re.M),
    re.compile(r"^\s*from\s+random\s+import", re.M),
    re.compile(r"\btime\.time\s*\(", re.M),
    re.compile(r"\bdatetime\.now\s*\(", re.M),
    re.compile(r"\bdatetime\.utcnow\s*\(", re.M),
    # bare global numpy RNG (np.random.rand etc.) -- the Generator API is fine.
    re.compile(r"\bnp\.random\.(?!Generator|default_rng)\w+", re.M),
    re.compile(r"\bnumpy\.random\.(?!Generator|default_rng|PCG64)\w+", re.M),
]


def _runtime_files():
    for pkg in _RUNTIME_PACKAGES:
        yield from (_PKG_ROOT / pkg).rglob("*.py")


def test_no_banned_primitives_in_runtime():
    offenders = []
    for path in _runtime_files():
        text = path.read_text(encoding="utf-8")
        for pat in _BANNED:
            if pat.search(text):
                offenders.append(f"{path.name}: {pat.pattern}")
    assert not offenders, "determinism violations found: " + "; ".join(offenders)


def test_no_llm_sdk_imported_in_runtime():
    """The runtime path must not import an LLM SDK."""
    llm = re.compile(r"^\s*import\s+(anthropic|openai)\b|from\s+(anthropic|openai)\s+import", re.M)
    offenders = [p.name for p in _runtime_files() if llm.search(p.read_text(encoding="utf-8"))]
    assert not offenders, f"LLM SDK imported in runtime: {offenders}"
