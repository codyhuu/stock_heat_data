from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    default_filter: str = "all-stocks"
    default_pages: int = 1
    database_path: Path = Path("data/stocks_heat.db")
    reports_dir: Path = Path("reports")
    alert_mentions_growth_pct: int = 100
    scheduler_interval_hours: int = 24
    feishu_webhook_url: str = ""
    feishu_secret: str = ""


def load_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()

    raw = _load_simple_toml(config_path)

    return AppConfig(
        default_filter=str(raw.get("default_filter", AppConfig.default_filter)),
        default_pages=int(raw.get("default_pages", AppConfig.default_pages)),
        database_path=Path(raw.get("database_path", AppConfig.database_path)),
        reports_dir=Path(raw.get("reports_dir", AppConfig.reports_dir)),
        alert_mentions_growth_pct=int(
            raw.get("alert_mentions_growth_pct", AppConfig.alert_mentions_growth_pct)
        ),
        scheduler_interval_hours=int(
            raw.get("scheduler_interval_hours", AppConfig.scheduler_interval_hours)
        ),
        feishu_webhook_url=os.getenv(
            "FEISHU_WEBHOOK_URL",
            str(raw.get("feishu_webhook_url", AppConfig.feishu_webhook_url)),
        ),
        feishu_secret=os.getenv(
            "FEISHU_SECRET",
            str(raw.get("feishu_secret", AppConfig.feishu_secret)),
        ),
    )


def _load_simple_toml(path: Path) -> dict[str, object]:
    values: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue
        key, value = cleaned.split("=", 1)
        values[key.strip()] = _parse_value(value.strip())
    return values


def _parse_value(value: str) -> object:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value
