"""Database helpers for ShopWorld application simulators."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

# Import model definitions so SQLModel.metadata includes all application tables
# before create_all() is called.
from shopworld.apps.shopify_admin import models as _shopify_models  # noqa: F401


class Database:
    """Small wrapper around a SQLModel engine used by tests and simulators."""

    def __init__(self, url: str):
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        engine_kwargs = {"connect_args": connect_args}

        # A plain sqlite:///:memory: engine creates a separate empty database for
        # each connection. StaticPool keeps one in-memory DB shared by every
        # session produced from this Database wrapper.
        if url == "sqlite:///:memory:":
            engine_kwargs["poolclass"] = StaticPool

        self.engine = create_engine(url, **engine_kwargs)
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a SQLModel Session bound to this database."""
        with Session(self.engine) as session:
            yield session


def init_database(database: str | Path = ":memory:") -> Database:
    """Initialize a ShopWorld database and create all known tables.

    Args:
        database: Either ``":memory:"`` for an in-memory SQLite database, a
            SQLite URL, or a filesystem path for a SQLite database file.
    """
    database_str = str(database)
    if database_str == ":memory:":
        url = "sqlite:///:memory:"
    elif database_str.startswith("sqlite"):
        url = database_str
    else:
        url = f"sqlite:///{database_str}"

    return Database(url)
