
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def url_modifier(url):
    try:
        if not url:
            return None

        url = url.strip()

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)

        if not (
            parsed.hostname == "flipkart.com"
            or parsed.hostname.endswith(".flipkart.com")
        ):
            return None

        path = parsed.path.rstrip("/")

        # Convert a product page to its review page,
        # keeping the product name in the URL.
        if "/product-reviews/" in path:
            review_path = path
        elif "/p/" in path:
            review_path = path.replace("/p/", "/product-reviews/", 1)
        else:
            return None

        # Keep the product PID and other useful parameters.
        # Remove any old page parameter.
        parameters = [
            (key, value)
            for key, value in parse_qsl(
                parsed.query, keep_blank_values=True
            )
            if key.lower() != "page"
        ]

        # Return a URL prefix because the existing scraper
        # appends the page number.
        query = urlencode(parameters)

        separator = "&" if query else "?"
        base_url = urlunparse((
            "https",
            parsed.netloc,
            review_path,
            "",
            query,
            ""
        ))

        return base_url + separator + "page="

    except Exception:
        return None
