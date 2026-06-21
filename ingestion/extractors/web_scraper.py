"""Simple CUSB webpage scraper."""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup


def scrape_page(url: str) -> dict:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")
    for node in soup(["script", "style", "nav", "footer", "header"]):
        node.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    return {"url": url, "title": title, "text": text}

