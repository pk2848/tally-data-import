"""Tests for snap_to_tally.matcher – name resolution logic."""

from pathlib import Path

import pytest

from snap_to_tally.database import MappingDatabase
from snap_to_tally.matcher import match_name, resolve_items, MatchResult


TALLY_ITEMS = [
    "Coca-Cola 500ml",
    "Pepsi 600ml",
    "Britannia Good Day",
    "Parle-G Biscuits",
    "Amul Butter 500g",
]


class TestMatchName:

    def test_exact_match_case_insensitive(self):
        result = match_name("coca-cola 500ml", TALLY_ITEMS)
        assert result.method == "exact"
        assert result.tally_name == "Coca-Cola 500ml"
        assert result.score == 100

    def test_fuzzy_match(self):
        result = match_name("Coca Cola 500 ml", TALLY_ITEMS, fuzzy_threshold=80)
        assert result.method == "fuzzy"
        assert result.tally_name == "Coca-Cola 500ml"
        assert result.score >= 80

    def test_unresolved(self):
        result = match_name("Random Unknown Item", TALLY_ITEMS)
        assert result.method == "unresolved"
        assert result.tally_name is None
        assert result.score == 0

    def test_history_match(self, tmp_path: Path):
        db = MappingDatabase(tmp_path / "test.db")
        db.save("Coke 500ml", "Coca-Cola 500ml")
        result = match_name("Coke 500ml", TALLY_ITEMS, db=db)
        assert result.method == "history"
        assert result.tally_name == "Coca-Cola 500ml"
        db.close()

    def test_exact_beats_fuzzy(self):
        result = match_name("Pepsi 600ml", TALLY_ITEMS)
        assert result.method == "exact"

    def test_history_used_before_fuzzy(self, tmp_path: Path):
        db = MappingDatabase(tmp_path / "test.db")
        # Map to something different from what fuzzy would find
        db.save("Coca Cola 500 ml", "Pepsi 600ml")
        result = match_name("Coca Cola 500 ml", TALLY_ITEMS, db=db)
        assert result.method == "history"
        assert result.tally_name == "Pepsi 600ml"
        db.close()


class TestResolveItems:

    def test_resolve_multiple(self):
        names = ["Coca-Cola 500ml", "Random Thing"]
        results = resolve_items(names, TALLY_ITEMS)
        assert len(results) == 2
        assert results[0].method == "exact"
        assert results[1].method == "unresolved"
