from datetime import datetime, timezone

from app.collectors.apewisdom import ApeWisdomItem
from app.reports.daily_report import generate_daily_report
from app.storage.database import save_snapshot


def test_generate_daily_report(tmp_path):
    db_path = tmp_path / "stocks_heat.db"
    reports_dir = tmp_path / "reports"
    save_snapshot(
        db_path,
        "all-stocks",
        [
            ApeWisdomItem(
                rank=1,
                ticker="NVDA",
                name="NVIDIA",
                mentions=20,
                upvotes=100,
                rank_24h_ago=10,
                mentions_24h_ago=5,
            )
        ],
        collected_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    report_path = generate_daily_report(db_path, reports_dir, "all-stocks")
    content = report_path.read_text(encoding="utf-8")

    assert "股票热度日报" in content
    assert "NVDA" in content
    assert "300.0%" in content
