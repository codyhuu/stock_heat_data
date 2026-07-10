from __future__ import annotations

import sqlite3


def top_by_mentions(rows: list[sqlite3.Row], limit: int = 20) -> list[sqlite3.Row]:
    return sorted(rows, key=lambda row: row["mentions"], reverse=True)[:limit]


def top_by_growth(rows: list[sqlite3.Row], limit: int = 20) -> list[sqlite3.Row]:
    candidates = [row for row in rows if row["mentions_growth_pct"] is not None]
    return sorted(candidates, key=lambda row: row["mentions_growth_pct"], reverse=True)[:limit]


def top_rank_climbers(rows: list[sqlite3.Row], limit: int = 20) -> list[sqlite3.Row]:
    candidates = [row for row in rows if row["rank_change"] is not None]
    return sorted(candidates, key=lambda row: row["rank_change"], reverse=True)[:limit]


def new_or_returning(rows: list[sqlite3.Row], limit: int = 20) -> list[sqlite3.Row]:
    candidates = [row for row in rows if row["rank_24h_ago"] is None]
    return sorted(candidates, key=lambda row: row["mentions"], reverse=True)[:limit]


def alert_rows(rows: list[sqlite3.Row], growth_threshold_pct: int) -> list[sqlite3.Row]:
    return [
        row
        for row in top_by_growth(rows, limit=len(rows))
        if row["mentions_growth_pct"] >= growth_threshold_pct
    ]

