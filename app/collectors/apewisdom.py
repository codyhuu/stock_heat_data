from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://apewisdom.io/api/v1.0/filter"
USER_AGENT = "stock-heat-tracker/0.1 (+local research project)"


class ApeWisdomError(RuntimeError):
    """Raised when ApeWisdom data cannot be fetched or parsed."""


@dataclass(frozen=True)
class ApeWisdomItem:
    rank: int
    ticker: str
    name: str
    mentions: int
    upvotes: int
    rank_24h_ago: int | None
    mentions_24h_ago: int | None

    @property
    def rank_change(self) -> int | None:
        if self.rank_24h_ago is None:
            return None
        return self.rank_24h_ago - self.rank

    @property
    def mentions_change(self) -> int | None:
        if self.mentions_24h_ago is None:
            return None
        return self.mentions - self.mentions_24h_ago

    @property
    def mentions_growth_pct(self) -> float | None:
        if not self.mentions_24h_ago:
            return None
        return (self.mentions - self.mentions_24h_ago) / self.mentions_24h_ago * 100


@dataclass(frozen=True)
class ApeWisdomPage:
    count: int
    pages: int
    current_page: int
    results: list[ApeWisdomItem]


def fetch_page(filter_name: str, page: int = 1, timeout: int = 30) -> ApeWisdomPage:
    url = f"{BASE_URL}/{filter_name}/page/{page}"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ApeWisdomError(f"ApeWisdom returned HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise ApeWisdomError(f"Could not connect to ApeWisdom: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ApeWisdomError("ApeWisdom returned invalid JSON") from exc

    return parse_page(payload)


def fetch_rankings(
    filter_name: str,
    pages: int | None = 1,
    fetch_all_pages: bool = False,
    timeout: int = 30,
) -> list[ApeWisdomItem]:
    first_page = fetch_page(filter_name, page=1, timeout=timeout)
    results = list(first_page.results)

    if fetch_all_pages:
        target_pages = first_page.pages
    else:
        target_pages = min(pages or 1, first_page.pages)

    for page in range(2, target_pages + 1):
        results.extend(fetch_page(filter_name, page=page, timeout=timeout).results)

    return results


def parse_page(payload: dict[str, Any]) -> ApeWisdomPage:
    return ApeWisdomPage(
        count=_to_int(payload.get("count")) or 0,
        pages=_to_int(payload.get("pages")) or 1,
        current_page=_to_int(payload.get("current_page")) or 1,
        results=[parse_item(item) for item in payload.get("results", [])],
    )


def parse_item(raw: dict[str, Any]) -> ApeWisdomItem:
    rank = _to_int(raw.get("rank"))
    mentions = _to_int(raw.get("mentions"))
    upvotes = _to_int(raw.get("upvotes"))
    if rank is None or mentions is None or upvotes is None:
        raise ApeWisdomError(f"Missing required numeric fields in item: {raw}")

    ticker = str(raw.get("ticker", "")).strip().upper()
    if not ticker:
        raise ApeWisdomError(f"Missing ticker in item: {raw}")

    return ApeWisdomItem(
        rank=rank,
        ticker=ticker,
        name=unescape(str(raw.get("name", "")).strip()),
        mentions=mentions,
        upvotes=upvotes,
        rank_24h_ago=_to_int(raw.get("rank_24h_ago")),
        mentions_24h_ago=_to_int(raw.get("mentions_24h_ago")),
    )


def _to_int(value: Any) -> int | None:
    if value in (None, "", "None", "null"):
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None
