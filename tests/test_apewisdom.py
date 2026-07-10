from app.collectors.apewisdom import parse_page


def test_parse_page_converts_numeric_fields():
    page = parse_page(
        {
            "count": "1",
            "pages": "1",
            "current_page": "1",
            "results": [
                {
                    "rank": "2",
                    "ticker": "nvda",
                    "name": "NVIDIA",
                    "mentions": "1,200",
                    "upvotes": "300",
                    "rank_24h_ago": "5",
                    "mentions_24h_ago": "600",
                }
            ],
        }
    )

    item = page.results[0]
    assert item.ticker == "NVDA"
    assert item.mentions == 1200
    assert item.rank_change == 3
    assert item.mentions_change == 600
    assert item.mentions_growth_pct == 100

