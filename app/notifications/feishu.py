from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FeishuError(RuntimeError):
    """Raised when a Feishu message cannot be sent."""


def send_text(
    webhook_url: str,
    text: str,
    secret: str = "",
    timeout: int = 15,
) -> dict[str, Any]:
    if not webhook_url:
        raise FeishuError("Feishu webhook URL is empty.")

    payload = build_text_payload(text, secret=secret)
    request = Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise FeishuError(f"Feishu returned HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise FeishuError(f"Could not connect to Feishu: {exc.reason}") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FeishuError(f"Feishu returned invalid JSON: {raw}") from exc

    if not _is_success(result):
        raise FeishuError(f"Feishu rejected the message: {result}")

    return result


def build_text_payload(
    text: str,
    secret: str = "",
    timestamp: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "msg_type": "text",
        "content": {"text": text},
    }
    if secret:
        ts = timestamp or int(time.time())
        payload["timestamp"] = str(ts)
        payload["sign"] = sign(ts, secret)
    return payload


def sign(timestamp: int, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def format_daily_message(
    source_filter: str,
    collected_at: str,
    item_count: int,
    top_rows: list[Any],
    alert_rows: list[Any],
    report_path: str | Path,
) -> str:
    lines = [
        f"股票热度日报 - {source_filter}",
        f"抓取时间：{collected_at}",
        f"收录数量：{item_count}",
        "",
        "今日 Top 10：",
    ]

    for row in top_rows[:10]:
        growth = _format_growth(row["mentions_growth_pct"])
        lines.append(
            f"{row['rank']}. {row['ticker']} - mentions {row['mentions']}, "
            f"upvotes {row['upvotes']}, growth {growth}"
        )

    if alert_rows:
        lines.extend(["", "增长预警："])
        for row in alert_rows[:10]:
            lines.append(
                f"{row['ticker']} mentions {row['mentions']} "
                f"({_format_growth(row['mentions_growth_pct'])})"
            )

    lines.extend(["", f"本地报告：{Path(report_path)}"])
    return "\n".join(lines)


def _format_growth(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def _is_success(result: dict[str, Any]) -> bool:
    if result.get("StatusCode") == 0:
        return True
    if result.get("code") == 0:
        return True
    if result.get("status_code") == 0:
        return True
    return False
