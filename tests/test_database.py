"""Tests for snap_to_tally.database – SQLite mapping store."""

import tempfile
from pathlib import Path

import pytest

from snap_to_tally.database import MappingDatabase


@pytest.fixture()
def db(tmp_path: Path):
    """Provide a fresh in-memory-like MappingDatabase for each test."""
    _db = MappingDatabase(tmp_path / "test_mappings.db")
    yield _db
    _db.close()


class TestMappingDatabase:

    def test_save_and_lookup(self, db: MappingDatabase):
        db.save("Coke 500ml", "Coca-Cola 500ml")
        assert db.lookup("Coke 500ml") == "Coca-Cola 500ml"

    def test_lookup_missing_returns_none(self, db: MappingDatabase):
        assert db.lookup("NonExistent") is None

    def test_save_overwrites(self, db: MappingDatabase):
        db.save("Coke 500ml", "Coca-Cola 500ml")
        db.save("Coke 500ml", "Coca-Cola 500ml PET")
        assert db.lookup("Coke 500ml") == "Coca-Cola 500ml PET"

    def test_all_mappings(self, db: MappingDatabase):
        db.save("A", "X")
        db.save("B", "Y")
        mappings = db.all_mappings()
        assert ("A", "X") in mappings
        assert ("B", "Y") in mappings

    def test_delete(self, db: MappingDatabase):
        db.save("A", "X")
        db.delete("A")
        assert db.lookup("A") is None
