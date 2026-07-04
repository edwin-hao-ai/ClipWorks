import logging
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _absolute_url(base: str, src: Optional[str]) -> Optional[str]:
    if not src:
        return None
    src = src.strip()
    if src.startswith("data:"):
        return None
    return urljoin(base, src)


def scrape_url(url: str) -> dict:
    """Fetch webpage metadata and image candidates."""
    result = {
        "url": url,
        "title": "",
        "description": "",
        "images": [],
        "favicon": None,
    }
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "ClipWorks/1.0"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            title_tag = soup.find("title")
            result["title"] = title_tag.get_text(strip=True) if title_tag else ""

            meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
            if meta_desc:
                result["description"] = meta_desc.get("content", "") or ""

            og_image = soup.find("meta", attrs={"property": "og:image"})
            if og_image:
                img_url = _absolute_url(url, og_image.get("content"))
                if img_url:
                    result["images"].append(img_url)

            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                img_url = _absolute_url(url, src)
                if img_url:
                    result["images"].append(img_url)

            favicon = soup.find("link", rel=lambda r: r and "icon" in r.lower())
            if favicon:
                result["favicon"] = _absolute_url(url, favicon.get("href"))

            # Deduplicate and limit
            seen = set()
            unique = []
            for img in result["images"]:
                if img not in seen and len(unique) < 6:
                    seen.add(img)
                    unique.append(img)
            result["images"] = unique

    except Exception as exc:
        logger.warning("scrape_url failed for %s: %s", url, exc)

    return result
