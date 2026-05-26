from typing import List, Dict

import requests
from bs4 import BeautifulSoup


class HTMLFetcher:
    def __init__(self, logger=None) -> None:
        self.logger = logger

    def fetch(self, url: str) -> List[Dict[str, str]]:
        if self.logger:
            self.logger.info(f"Fetching HTML page: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            if self.logger:
                self.logger.exception(f"HTML fetch failed: {url}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = []

        for link in soup.find_all("a", href=True)[:10]:
            title = link.get_text(strip=True)
            if not title:
                continue

            items.append(
                {
                    "id": link["href"],
                    "title": title,
                    "link": link["href"],
                    "summary": title,
                }
            )

        if self.logger:
            self.logger.info(f"HTML fetch succeeded: {url} ({len(items)} entries)")

        return items