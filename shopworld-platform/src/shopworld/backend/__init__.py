"""Shared backend infrastructure for the ShopWorld platform."""

from shopworld.backend.db import Database, init_database

__all__ = ["Database", "init_database"]
