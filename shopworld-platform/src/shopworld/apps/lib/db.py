"""Compatibility shim for backend database helpers.

Prefer importing from :mod:`shopworld.backend.db` in new code.
"""

from shopworld.backend.db import Database, init_database

__all__ = ["Database", "init_database"]
