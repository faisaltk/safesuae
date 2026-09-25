#!/usr/bin/env python3
"""
Import permitted SafeOne product images for the ZEN GROUP catalogue.

The catalogue is discovered from SafeOne's product-category pages. Product
pages are fetched only when they match a product already present in our
catalogue. The requested catalogue contains no weapon-related products.
"""

from __future__ import annotations

import html
import re
import time
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image

BASE = "https://www.safeoneuae.com"
START_URL = f"{BASE}/en/products"

PRODUCT_FILE = Path("products/product-detail.html")
IMAGE_DIR = Path("products/images")
SKIP = {"eagle-es-100"}

session = requests.Session()
session.headers.update({"User-Agent": "ZEN-GROUP-permitted-product-image-import/1.0"})


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def read_targets() -> dict[str, str]:
    text = PRODUCT_FILE.read_text(encoding="utf-8")
    pairs = re.findall(r'{"slug":"([^"]+)","name":"([^"]+)"', text)
    return {slug: html.unescape(name) for slug, name in pairs}


def safe_category_links(soup: BeautifulSoup, page_url: str) -> set[str]:
    links: set[str] = set()
    host = urlparse(BASE).netloc

    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"]).split("#", 1)[0]
        parsed = urlparse(href)

        if parsed.netloc != host:
            continue
        if not parsed.path.startswith("/en/products/"):
            continue
        if "gun" in parsed.path.lower():
            continue

        links.add(href)

    return links


def category_pages() -> list[str]:
    """Discover SafeOne category pages and their pagination pages."""
    seen: set[str] = set()
    queue = [START_URL]

    while queue and len(seen) < 100:
        url = queue.pop(0)
        if url in seen:
            continue

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as exc:
            print(f"CATALOG ERROR: {url}: {exc}")
            continue

        seen.add(url)
        soup = BeautifulSoup(r.text, "html.parser")

        # From the main catalogue, discover category pages.
        # From a category page, also follow its pagination links.
        base_path = urlparse(url).path
        host = urlparse(BASE).netloc

        for href in safe_category_links(soup, url):
            parsed = urlparse(href)
            if parsed.path == base_path or url == START_URL:
                if href not in seen:
                    queue.append(href)

        # Pagination commonly keeps the same category path with a query string.
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"]).split("#", 1)[0]
            parsed = urlparse(href)
            if parsed.netloc == host and parsed.path == base_path:
                if href not in seen:
                    queue.append(href)

    return sorted(seen)


def product_urls() -> dict[str, str]:
    """Return product URL -> visible link text from permitted categories."""
    products: dict[str, str] = {}

    for category_url in category_pages():
        try:
            r = session.get(category_url, timeout=30)
            r.raise_for_status()
        except Exception as exc:
            print(f"CATEGORY ERROR: {category_url}: {exc}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = urljoin(category_url, a["href"]).split("#", 1)[0]
            if "/en/product-details/" not in href:
                continue

            label = " ".join(a.get_text(" ", strip=True).split())
            products[href] = label

    return products


def score_candidate(name: str, slug: str, url: str, label: str) -> float:
    target = norm(name)
    target_slug = norm(slug)
    url_part = norm(urlparse(url).path.rsplit("/", 1)[-1])
    label_norm = norm(label)

    score = 0.0

    # Exact product-name matches are the strongest signal.
    if target and target == label_norm:
        score += 500.0
    elif target and target in label_norm:
        score += 250.0

    # Match the actual SafeOne URL slug, not the local website slug.
    score += 100.0 * SequenceMatcher(None, target_slug, url_part).ratio()

    # Model tokens are important for variants such as EL/KL, A43/A59, etc.
    model_tokens = re.findall(r"[a-z]*\d+[a-z]*", name.lower())
    matched_tokens = 0
    for token in model_tokens:
        token_norm = norm(token)
        if token_norm and (token_norm in url_part or token_norm in label_norm):
            matched_tokens += 1
            score += 80.0

    # Brand/model labels should agree with the target.
    brand = name.split()[0].lower()
    if norm(brand) and norm(brand) in url_part:
        score += 30.0

    score += 40.0 * SequenceMatcher(None, target, label_norm).ratio()

    # Penalize candidates that do not contain the distinctive model tokens.
    if model_tokens and matched_tokens == 0:
        score -= 250.0

    return score


def find_url(name: str, slug: str, products: dict[str, str]) -> str | None:
    ranked = sorted(
        (
            (score_candidate(name, slug, url, label), url)
            for url, label in products.items()
        ),
        reverse=True,
    )

    if not ranked:
        return None

    score, url = ranked[0]
    if score < 100:
        return None

    return url


def save_as_webp(data: bytes, output: Path) -> None:
    image = Image.open(BytesIO(data)).convert("RGB")
    image.save(output, "WEBP", quality=88, method=6)


def main() -> int:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    targets = read_targets()
    products = product_urls()

    print(f"Found {len(products)} permitted-category product pages.")
    print(f"Matching against {len(targets)} website products.")

    downloaded = skipped = missing = 0

    for slug, name in targets.items():
        # Refresh existing imported images so incorrect duplicate matches are repaired.
        if slug in SKIP and (IMAGE_DIR / "ES-100.webp").exists():
            print(f"SKIP existing image: {name}")
            skipped += 1
            continue

        source_url = find_url(name, slug, products)
        if not source_url:
            print(f"NOT FOUND: {name}")
            missing += 1
            continue

        try:
            page = session.get(source_url, timeout=30)
            page.raise_for_status()
            soup = BeautifulSoup(page.text, "html.parser")

            image_url = None
            for attrs in (
                {"property": "og:image"},
                {"name": "twitter:image"},
            ):
                tag = soup.find("meta", attrs=attrs)
                if tag and tag.get("content"):
                    image_url = urljoin(source_url, tag["content"])
                    break

            if not image_url:
                for img in soup.find_all("img"):
                    src = img.get("src") or img.get("data-src")
                    if src and "logo" not in src.lower() and "whatsapp" not in src.lower():
                        image_url = urljoin(source_url, src)
                        break

            if not image_url:
                print(f"NO IMAGE: {name}")
                missing += 1
                continue

            image = session.get(image_url, timeout=30)
            image.raise_for_status()

            output = IMAGE_DIR / f"{slug}.webp"
            save_as_webp(image.content, output)
            print(f"OK: {name} -> {output}")
            downloaded += 1
            time.sleep(0.25)

        except Exception as exc:
            print(f"ERROR: {name}: {exc}")
            missing += 1

    print(f"Downloaded: {downloaded}")
    print(f"Skipped existing: {skipped}")
    print(f"Missing/errors: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
