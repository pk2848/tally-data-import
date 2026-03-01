"""SQLite database for persisting historical item-name mappings.

Each row stores a mapping from a *bill item name* (as seen on a supplier's
invoice) to the corresponding *Tally item name* so that the same mapping can
be reused automatically on future imports.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

_DEFAULT_DB = Path("snap_to_tally_mappings.db")

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS item_mappings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_name     TEXT    NOT NULL,
    tally_name    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now')),
    UNIQUE(bill_name)
);

CREATE TABLE IF NOT EXISTS config (
    key           TEXT    PRIMARY KEY,
    value         TEXT    NOT NULL
);
"""


class MappingDatabase:
    """Thin wrapper around an SQLite database of historical mappings."""

    def __init__(self, db_path: str | Path = _DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── config ──────────────────────────────────────────────────────────

    def get_config(self, key: str) -> Optional[str]:
        """Retrieve a configuration value by key."""
        row = self._conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set_config(self, key: str, value: str) -> None:
        """Store or update a configuration value."""
        self._conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    # ── queries ──────────────────────────────────────────────────────

    def lookup(self, bill_name: str) -> Optional[str]:
        """Return the Tally name previously mapped to *bill_name*, or None."""
        row = self._conn.execute(
            "SELECT tally_name FROM item_mappings WHERE bill_name = ?",
            (bill_name,),
        ).fetchone()
        return row[0] if row else None

    def save(self, bill_name: str, tally_name: str) -> None:
        """Insert or update a mapping."""
        self._conn.execute(
            "INSERT INTO item_mappings (bill_name, tally_name) "
            "VALUES (?, ?) "
            "ON CONFLICT(bill_name) DO UPDATE SET tally_name = excluded.tally_name",
            (bill_name, tally_name),
        )
        self._conn.commit()

    def all_mappings(self) -> list[tuple[str, str]]:
        """Return all ``(bill_name, tally_name)`` pairs."""
        return self._conn.execute(
            "SELECT bill_name, tally_name FROM item_mappings ORDER BY bill_name"
        ).fetchall()

    def delete(self, bill_name: str) -> None:
        """Remove a mapping by bill name."""
        self._conn.execute(
            "DELETE FROM item_mappings WHERE bill_name = ?", (bill_name,)
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "MappingDatabase":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
