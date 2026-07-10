from app.notifications.feishu import build_text_payload, format_daily_message, sign


def test_build_text_payload_without_secret():
    payload = build_text_payload("hello")

    assert payload == {
        "msg_type": "text",
        "content": {"text": "hello"},
    }


def test_build_text_payload_with_secret():
    payload = build_text_payload("hello", secret="abc", timestamp=123)

    assert payload["timestamp"] == "123"
    assert payload["sign"] == sign(123, "abc")
    assert payload["content"]["text"] == "hello"


def test_format_daily_message():
    rows = [
        {
            "rank": 1,
            "ticker": "NVDA",
            "mentions": 100,
            "upvotes": 200,
            "mentions_growth_pct": 50.0,
        }
    ]

    message = format_daily_message(
        source_filter="all-stocks",
        collected_at="2026-07-10T09:00:00+08:00",
        item_count=100,
        top_rows=rows,
        alert_rows=rows,
        report_path="reports/daily.md",
    )

    assert "股票热度日报 - all-stocks" in message
    assert "NVDA" in message
    assert "reports/daily.md" in message
