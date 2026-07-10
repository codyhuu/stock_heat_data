from __future__ import annotations

import argparse
import sys

from app.collectors.apewisdom import ApeWisdomError, fetch_rankings
from app.config import load_config
from app.notifications.feishu import FeishuError, send_text
from app.reports.daily_report import generate_daily_report, send_daily_report_to_feishu
from app.scheduler import run_scheduler
from app.storage.database import init_db, save_snapshot, ticker_history


def main(argv: list[str] | None = None) -> int:
    config = load_config()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init-db":
            init_db(config.database_path)
            print(f"Database is ready: {config.database_path}")
            return 0

        if args.command == "collect":
            pages = args.pages if args.pages is not None else config.default_pages
            source_filter = args.filter or config.default_filter
            items = fetch_rankings(
                source_filter,
                pages=pages,
                fetch_all_pages=args.all_pages,
            )
            snapshot_id = save_snapshot(config.database_path, source_filter, items)
            print(f"Saved snapshot {snapshot_id} with {len(items)} rows.")
            return 0

        if args.command == "report":
            report_path = generate_daily_report(
                config.database_path,
                config.reports_dir,
                source_filter=args.filter,
                growth_threshold_pct=config.alert_mentions_growth_pct,
            )
            print(f"Report generated: {report_path}")
            if config.feishu_webhook_url and not args.no_feishu:
                send_daily_report_to_feishu(
                    config.database_path,
                    report_path,
                    webhook_url=config.feishu_webhook_url,
                    secret=config.feishu_secret,
                    source_filter=args.filter,
                    growth_threshold_pct=config.alert_mentions_growth_pct,
                )
                print("Feishu message sent.")
            return 0

        if args.command == "history":
            rows = ticker_history(
                config.database_path,
                args.ticker,
                limit=args.limit,
                source_filter=args.filter,
            )
            print_history(rows)
            return 0

        if args.command == "run-scheduler":
            pages = args.pages if args.pages is not None else config.default_pages
            source_filter = args.filter or config.default_filter
            print(
                f"Scheduler started: filter={source_filter}, every={config.scheduler_interval_hours}h"
            )
            run_scheduler(
                config.database_path,
                config.reports_dir,
                source_filter=source_filter,
                pages=pages,
                interval_hours=config.scheduler_interval_hours,
                fetch_all_pages=args.all_pages,
                growth_threshold_pct=config.alert_mentions_growth_pct,
                feishu_webhook_url=config.feishu_webhook_url,
                feishu_secret=config.feishu_secret,
            )
            return 0

        if args.command == "test-feishu":
            if not config.feishu_webhook_url:
                raise RuntimeError("Please set feishu_webhook_url in config.toml first.")
            send_text(
                config.feishu_webhook_url,
                "Stock Heat Tracker 飞书测试消息：连接成功。",
                secret=config.feishu_secret,
            )
            print("Feishu test message sent.")
            return 0

        parser.print_help()
        return 1
    except FeishuError as exc:
        print(f"Feishu error: {exc}", file=sys.stderr)
        return 4
    except ApeWisdomError as exc:
        print(f"ApeWisdom error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock-heat-tracker",
        description="Collect ApeWisdom stock ticker heat data.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db", help="Create the SQLite database and tables.")

    collect = subparsers.add_parser("collect", help="Fetch ApeWisdom data and save it.")
    collect.add_argument("--filter", help="ApeWisdom filter, e.g. all-stocks.")
    collect.add_argument("--pages", type=int, help="Number of pages to fetch.")
    collect.add_argument("--all-pages", action="store_true", help="Fetch every available page.")

    report = subparsers.add_parser("report", help="Generate a Markdown report.")
    report.add_argument("--filter", help="Use the latest snapshot for this filter.")
    report.add_argument("--no-feishu", action="store_true", help="Do not send Feishu notification.")

    history = subparsers.add_parser("history", help="Show recent history for one ticker.")
    history.add_argument("ticker")
    history.add_argument("--filter", help="Filter history by ApeWisdom source.")
    history.add_argument("--limit", type=int, default=30)

    scheduler = subparsers.add_parser("run-scheduler", help="Collect and report every 24h.")
    scheduler.add_argument("--filter", help="ApeWisdom filter, e.g. all-stocks.")
    scheduler.add_argument("--pages", type=int, help="Number of pages to fetch.")
    scheduler.add_argument("--all-pages", action="store_true", help="Fetch every available page.")

    subparsers.add_parser("test-feishu", help="Send a test message to Feishu.")

    return parser


def print_history(rows: list[object]) -> None:
    if not rows:
        print("No history found.")
        return

    print("Collected At | Filter | Rank | Ticker | Mentions | Upvotes | Growth")
    print("--- | --- | ---: | --- | ---: | ---: | ---:")
    for row in rows:
        growth = "-"
        if row["mentions_growth_pct"] is not None:
            growth = f"{row['mentions_growth_pct']:.1f}%"
        print(
            f"{row['collected_at']} | {row['source_filter']} | {row['rank']} | "
            f"{row['ticker']} | {row['mentions']} | {row['upvotes']} | {growth}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
