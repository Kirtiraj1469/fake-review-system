"""Flipkart review scraper compatible with home_page.py.

Returns (rating, review_text, username, date) tuples.
Unknown metadata is left blank rather than fabricated.
"""
import logging
import re
import time
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup
from app.url_modifier import url_modifier

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()



def extract_reviews_from_page(soup: BeautifulSoup) -> List[Tuple[str, str, str, str]]:
    """Extract Flipkart reviews using embedded JSON, with HTML fallback."""
    if soup is None:
        return []

    # First try Flipkart's embedded review data.
    import json

    for script in soup.find_all("script"):
        content = script.string or ""
        marker = "window.__INITIAL_STATE__"

        if marker not in content:
            continue

        try:
            match = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*",
                content
            )
            if not match:
                continue

            data, _ = json.JSONDecoder().raw_decode(
                content[match.end():]
            )

            slots = (
                data.get("multiWidgetState", {})
                .get("widgetsData", {})
                .get("slots", [])
            )

            results = []
            seen = set()

            for slot in slots:
                widget = slot.get("slotData", {}).get("widget", {})
                components = (
                    widget.get("data", {})
                    .get("renderableComponents", [])
                )

                for component in components:
                    value = component.get("value", {})

                    if not isinstance(value, dict):
                        continue

                    rating = value.get("rating")
                    title = value.get("title", "")
                    body = value.get("text", "")

                    # Only accept actual review records.
                    if not isinstance(rating, (int, float)):
                        continue

                    if not 1 <= rating <= 5:
                        continue

                    if not isinstance(title, str):
                        title = ""
                    if not isinstance(body, str):
                        body = ""

                    title = normalize_text(title)
                    body = normalize_text(body)

                    combined = normalize_text(
                        f"{title}. {body}" if title and body
                        else title or body
                    )

                    if not combined or combined in seen:
                        continue

                    results.append((
                        str(rating),
                        combined,
                        "",
                        ""
                    ))
                    seen.add(combined)

            if results:
                logger.info(
                    "Extracted %s reviews with real ratings",
                    len(results)
                )
                return results

        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            logger.warning(
                "Could not parse embedded Flipkart reviews: %s",
                exc
            )

    # Fallback: preserve the existing working HTML scraper.
    nodes = soup.select("div.r-op4f77")

    if not nodes:
        logger.warning("No Flipkart review elements found")
        return []

    results = []
    seen = set()
    pending_title = ""

    for node in nodes:
        text = normalize_text(node.get_text(" ", strip=True))

        if not text:
            continue

        is_body = (
            node.find("span", class_="css-1jxf684")
            is not None
        )

        if not is_body:
            pending_title = text
            continue

        body = re.sub(
            r"\s+more$",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

        combined = normalize_text(
            f"{pending_title}. {body}"
            if pending_title else body
        )

        pending_title = ""

        if combined and combined not in seen:
            results.append(("", combined, "", ""))
            seen.add(combined)

    if pending_title:
        title = normalize_text(pending_title)
        if title and title not in seen:
            results.append(("", title, "", ""))

    return results



def get_reviews(start_page: int, end_page: int, url: str) -> List[Tuple[str, str, str, str]]:
    """Fetch requested review pages; preserve the existing four-column interface."""
    base = url_modifier(url)
    if not base:
        logger.warning("Invalid or unsupported Flipkart URL: %s", url)
        return []

    if start_page < 1 or end_page < start_page:
        return []

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    })
    all_reviews = []
    seen = set()

    for page_num in range(start_page, end_page + 1):
        page_url = f"{base}{page_num}"
        try:
            response = session.get(page_url, timeout=20)
            if response.status_code in (403, 429):
                logger.warning("Flipkart blocked or rate-limited page %s: HTTP %s", page_num, response.status_code)
                break
            if response.status_code != 200:
                logger.warning("Flipkart page %s returned HTTP %s", page_num, response.status_code)
                break
            soup = BeautifulSoup(response.content, "html.parser")
            page_reviews = extract_reviews_from_page(soup)
            if not page_reviews:
                logger.warning("No reviews extracted on page %s", page_num)
                break
            new_count = 0
            for review in page_reviews:
                if review[1] not in seen:
                    seen.add(review[1])
                    all_reviews.append(review)
                    new_count += 1
            if new_count == 0:
                logger.warning("Page %s contained no new reviews; stopping", page_num)
                break
        except requests.RequestException as exc:
            logger.warning("Error fetching page %s: %s", page_num, exc)
            break
        if page_num < end_page:
            time.sleep(1)

    return all_reviews
