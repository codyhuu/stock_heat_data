from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Iterator

from app.collectors.apewisdom import ApeWisdomItem


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filter TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    item_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    source_filter TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    rank INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    mentions INTEGER NOT NULL,
    upvotes INTEGER NOT NULL,
    rank_24h_ago INTEGER,
    mentions_24h_ago INTEGER,
    rank_change INTEGER,
    mentions_change INTEGER,
    mentions_growth_pct REAL,
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_ticker_mentions_ticker_time
ON ticker_mentions(ticker, collected_at);

CREATE INDEX IF NOT EXISTS idx_ticker_mentions_filter_time
ON ticker_mentions(source_filter, collected_at);
"""


@contextmanager
def connect(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    db_path = Path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db(database_path: str | Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)


def save_snapshot(
    database_path: str | Path,
    source_filter: str,
    items: list[ApeWisdomItem],
    collected_at: datetime | None = None,
) -> int:
    init_db(database_path)
    timestamp = (collected_at or datetime.now().astimezone()).isoformat(timespec="seconds")

    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO snapshots (source_filter, collected_at, item_count)
            VALUES (?, ?, ?)
            """,
            (source_filter, timestamp, len(items)),
        )
        snapshot_id = int(cursor.lastrowid)

        connection.executemany(
            """
            INSERT INTO ticker_mentions (
                snapshot_id,
                source_filter,
                collected_at,
                rank,
                ticker,
                name,
                mentions,
                upvotes,
                rank_24h_ago,
                mentions_24h_ago,
                rank_change,
                mentions_change,
                mentions_growth_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id,
                    source_filter,
                    timestamp,
                    item.rank,
                    item.ticker,
                    item.name,
                    item.mentions,
                    item.upvotes,
                    item.rank_24h_ago,
                    item.mentions_24h_ago,
                    item.rank_change,
                    item.mentions_change,
                    item.mentions_growth_pct,
                )
                for item in items
            ],
        )

    return snapshot_id


def latest_snapshot(database_path: str | Path, source_filter: str | None = None) -> sqlite3.Row | None:
    init_db(database_path)
    with connect(database_path) as connection:
        if source_filter:
            return connection.execute(
                """
                SELECT * FROM snapshots
                WHERE source_filter = ?
                ORDER BY collected_at DESC, id DESC
                LIMIT 1
                """,
                (source_filter,),
            ).fetchone()

        return connection.execute(
            """
            SELECT * FROM snapshots
            ORDER BY collected_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()


def snapshot_items(database_path: str | Path, snapshot_id: int) -> list[sqlite3.Row]:
    init_db(database_path)
    with connect(database_path) as connection:
        return list(
            connection.execute(
                """
                SELECT * FROM ticker_mentions
                WHERE snapshot_id = ?
                ORDER BY rank ASC
                """,
                (snapshot_id,),
            ).fetchall()
        )


def ticker_history(
    database_path: str | Path,
    ticker: str,
    limit: int = 30,
    source_filter: str | None = None,
) -> list[sqlite3.Row]:
    init_db(database_path)
    ticker = ticker.upper()
    with connect(database_path) as connection:
        if source_filter:
            return list(
                connection.execute(
                    """
                    SELECT * FROM ticker_mentions
                    WHERE ticker = ? AND source_filter = ?
                    ORDER BY collected_at DESC
                    LIMIT ?
                    """,
                    (ticker, source_filter, limit),
                ).fetchall()
            )

        return list(
            connection.execute(
                """
                SELECT * FROM ticker_mentions
                WHERE ticker = ?
                ORDER BY collected_at DESC
                LIMIT ?
                """,
                (ticker, limit),
            ).fetchall()
        )
