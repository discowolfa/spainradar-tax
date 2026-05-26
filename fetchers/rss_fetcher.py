from typing import List, Dict

import feedparser


class RSSFetcher:
    def __init__(self, logger=None) -> None:
        self.logger = logger

    def fetch(self, url: str) -> List[Dict[str, str]]:
        if self.logger:
            self.logger.info(f"Fetching RSS feed: {url}")

        try:
            feed = feedparser.parse(url)
        except Exception:
            if self.logger:
                self.logger.exception(f"RSS fetch failed: {url}")
            return []

        if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
            if self.logger:
                self.logger.warning(
                    "RSS feed parse failed: %s (%s)",
                    url,
                    getattr(feed, "bozo_exception", "unknown error"),
                )
            return []

        items = []

        for entry in feed.entries:
            items.append(
                {
                    "id": entry.get("id", entry.get("link", "")),
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                }
            )

        if self.logger:
            self.logger.info(f"RSS fetch succeeded: {url} ({len(items)} entries)")

        return items