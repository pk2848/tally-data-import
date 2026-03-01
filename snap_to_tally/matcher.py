"""Module B (part 2): Master matching – resolves bill item names to Tally
master names using exact match → fuzzy match → historical DB → manual."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from thefuzz import fuzz

from snap_to_tally.database import MappingDatabase

# Minimum fuzzy-match score (0-100) to consider a candidate.
DEFAULT_FUZZY_THRESHOLD = 85


@dataclass
class MatchResult:
    """Outcome of a single name-resolution attempt."""

    bill_name: str
    tally_name: Optional[str]
    method: str  # "exact" | "fuzzy" | "history" | "manual" | "unresolved"
    score: int = 100  # 0-100; 100 for exact / history


def match_name(
    bill_name: str,
    tally_names: list[str],
    db: MappingDatabase | None = None,
    fuzzy_threshold: int = DEFAULT_FUZZY_THRESHOLD,
) -> MatchResult:
    """Resolve *bill_name* against a list of Tally master names.

    Resolution order:
    1. **Exact match** (case-insensitive).
    2. **History match** from the SQLite mapping database.
    3. **Fuzzy match** using ``thefuzz`` with a configurable threshold.
    4. Returns *unresolved* if nothing is found.
    """
    normalised_bill = bill_name.strip().lower()

    # 1. Exact match
    for tname in tally_names:
        if tname.strip().lower() == normalised_bill:
            return MatchResult(bill_name, tname, "exact", 100)

    # 2. History match from local DB
    if db is not None:
        history_name = db.lookup(bill_name)
        if history_name is not None:
            return MatchResult(bill_name, history_name, "history", 100)

    # 3. Fuzzy match
    best_score = 0
    best_match: str | None = None
    for tname in tally_names:
        score = fuzz.token_sort_ratio(normalised_bill, tname.strip().lower())
        if score > best_score:
            best_score = score
            best_match = tname
    if best_match is not None and best_score >= fuzzy_threshold:
        return MatchResult(bill_name, best_match, "fuzzy", best_score)

    # 4. Unresolved
    return MatchResult(bill_name, None, "unresolved", 0)


def resolve_items(
    bill_items: list[str],
    tally_names: list[str],
    db: MappingDatabase | None = None,
    fuzzy_threshold: int = DEFAULT_FUZZY_THRESHOLD,
) -> list[MatchResult]:
    """Resolve a list of bill item names and return a list of MatchResults."""
    return [
        match_name(name, tally_names, db=db, fuzzy_threshold=fuzzy_threshold)
        for name in bill_items
    ]
