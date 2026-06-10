"""
news_feed.py — Pulls recent crypto headlines from free RSS feeds (no API key
needed). The headlines get summarised down to title + short blurb and handed to
the AI brain so it can factor "what's happening right now" into its read.
"""

import time
from datetime import datetime, timedelta, timezone

import feedparser


def fetch_headlines(feeds: list, lookback_hours: int = 12, max_items: int = 25) -> list:
    """Return a list of recent {title, summary, source, published} dicts."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items = []

    for url in feeds:
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue  # a broken feed shouldn't crash the whole run

        source = parsed.feed.get("title", url)
        for entry in parsed.entries:
            published = None
            if getattr(entry, "published_parsed", None):
                published = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)

            # Skip anything older than our lookback window (keep undated items).
            if published is not None and published < cutoff:
                continue

            summary = getattr(entry, "summary", "") or ""
            items.append(
                {
                    "title": getattr(entry, "title", "(no title)"),
                    "summary": summary[:300],  # keep it short to save tokens
                    "source": source,
                    "published": published.isoformat() if published else "unknown",
                }
            )

    # Newest first; undated items sink to the bottom.
    items.sort(key=lambda x: x["published"], reverse=True)
    return items[:max_items]


def format_for_prompt(headlines: list) -> str:
    """Turn the headline list into a compact text block for the AI prompt."""
    if not headlines:
        return "(no recent headlines found)"
    lines = []
    for h in headlines:
        lines.append(f"- [{h['source']}] {h['title']}")
        if h["summary"]:
            lines.append(f"    {h['summary']}")
    return "\n".join(lines)
