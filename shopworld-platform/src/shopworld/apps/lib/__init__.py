"""Compatibility shims for shared backend infrastructure.

Prefer importing from :mod:`shopworld.backend` in new code.
"""

from shopworld.backend import Database, init_database

__all__ = ["Database", "init_database"]
