from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

from app.analysis.trend import alert_rows, new_or_returning, top_by_growth, top_by_mentions, top_rank_climbers
from app.notifications.feishu import format_daily_message, send_text
from app.storage.database import latest_snapshot, snapshot_items


def generate_daily_report(
    database_path: str | Path,
    reports_dir: str | Path,
    source_filter: str | None = None,
    growth_threshold_pct: int = 100,
) -> Path:
    snapshot = latest_snapshot(database_path, source_filter=source_filter)
    if snapshot is None:
        raise RuntimeError("No snapshot found. Run collect first.")

    rows = snapshot_items(database_path, snapshot["id"])
    report_dir = Path(reports_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    collected_at = datetime.fromisoformat(snapshot["collected_at"])
    date_label = collected_at.date().isoformat()
    filter_label = snapshot["source_filter"]
    report_path = report_dir / f"daily_heat_{filter_label}_{date_label}.md"
    report_path.write_text(
        build_report(snapshot, rows, growth_threshold_pct),
        encoding="utf-8",
    )
    return report_path


def send_daily_report_to_feishu(
    database_path: str | Path,
    report_path: str | Path,
    webhook_url: str,
    secret: str = "",
    source_filter: str | None = None,
    growth_threshold_pct: int = 100,
) -> None:
    if not webhook_url:
        return

    snapshot = latest_snapshot(database_path, source_filter=source_filter)
    if snapshot is None:
        raise RuntimeError("No snapshot found. Run collect first.")

    rows = snapshot_items(database_path, snapshot["id"])
    message = format_daily_message(
        source_filter=snapshot["source_filter"],
        collected_at=snapshot["collected_at"],
        item_count=snapshot["item_count"],
        top_rows=top_by_mentions(rows, 10),
        alert_rows=alert_rows(rows, growth_threshold_pct),
        report_path=report_path,
    )
    send_text(webhook_url, message, secret=secret)


def build_report(
    snapshot: sqlite3.Row,
    rows: list[sqlite3.Row],
    growth_threshold_pct: int = 100,
) -> str:
    collected_at = snapshot["collected_at"]
    lines = [
        f"# 股票热度日报 - {snapshot['source_filter']}",
        "",
        f"- 抓取时间：`{collected_at}`",
        f"- 收录数量：`{snapshot['item_count']}`",
        f"- 预警阈值：mentions 增长大于等于 `{growth_threshold_pct}%`",
        "",
        "## 今日 Top 20",
        "",
        _table(top_by_mentions(rows, 20)),
        "",
        "## Mentions 增长最快",
        "",
        _table(top_by_growth(rows, 20)),
        "",
        "## 排名上升最快",
        "",
        _table(top_rank_climbers(rows, 20)),
        "",
        "## 新上榜或缺少昨日排名",
        "",
        _table(new_or_returning(rows, 20)),
        "",
        f"## 增长预警（>={growth_threshold_pct}%）",
        "",
        _table(alert_rows(rows, growth_threshold_pct)),
        "",
    ]
    return "\n".join(lines)


def _table(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "_暂无数据_"

    table = [
        "| Rank | Ticker | Name | Mentions | Upvotes | Rank 24h Ago | Mentions 24h Ago | Rank Change | Mentions Change | Growth |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        table.append(
            "| "
            + " | ".join(
                [
                    str(row["rank"]),
                    str(row["ticker"]),
                    _escape_pipe(row["name"]),
                    str(row["mentions"]),
                    str(row["upvotes"]),
                    _display(row["rank_24h_ago"]),
                    _display(row["mentions_24h_ago"]),
                    _display(row["rank_change"], signed=True),
                    _display(row["mentions_change"], signed=True),
                    _display_pct(row["mentions_growth_pct"]),
                ]
            )
            + " |"
        )
    return "\n".join(table)


def _display(value: object, signed: bool = False) -> str:
    if value is None:
        return "-"
    if signed and isinstance(value, int) and value > 0:
        return f"+{value}"
    return str(value)


def _display_pct(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def _escape_pipe(value: str) -> str:
    return value.replace("|", "\\|")
