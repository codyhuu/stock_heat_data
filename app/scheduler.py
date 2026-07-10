from __future__ import annotations

import time
from pathlib import Path

from app.collectors.apewisdom import fetch_rankings
from app.reports.daily_report import generate_daily_report, send_daily_report_to_feishu
from app.storage.database import save_snapshot


def run_scheduler(
    database_path: str | Path,
    reports_dir: str | Path,
    source_filter: str,
    pages: int,
    interval_hours: int = 24,
    fetch_all_pages: bool = False,
    growth_threshold_pct: int = 100,
    feishu_webhook_url: str = "",
    feishu_secret: str = "",
) -> None:
    interval_seconds = interval_hours * 60 * 60
    while True:
        items = fetch_rankings(
            source_filter,
            pages=pages,
            fetch_all_pages=fetch_all_pages,
        )
        save_snapshot(database_path, source_filter, items)
        report_path = generate_daily_report(
            database_path,
            reports_dir,
            source_filter=source_filter,
            growth_threshold_pct=growth_threshold_pct,
        )
        send_daily_report_to_feishu(
            database_path,
            report_path,
            webhook_url=feishu_webhook_url,
            secret=feishu_secret,
            source_filter=source_filter,
            growth_threshold_pct=growth_threshold_pct,
        )
        time.sleep(interval_seconds)
