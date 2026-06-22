"""milli.run: a neuro-symbolic merchant runtime under test.

milli.run uses shallow NLU (an SVM/FastText-style linear classifier), regex
entity extraction, a confidence router, deterministic workflow state machines,
and policy/transaction guards. It accesses ShopWorld only through the Merchant
API Surface, exactly like the LLM agent (README §7 module ownership).

This package is a sibling of ``shopworld`` and is never imported by ShopWorld
core, preserving environment separation (README §13).
"""

from milli_run.agent import MilliRunAgent

__all__ = ["MilliRunAgent"]
