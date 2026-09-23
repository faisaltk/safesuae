#!/usr/bin/env python3
"""
Import permitted SafeOne product images for the ZEN GROUP catalogue.

Only the SafeOne categories used by this catalogue are visited. Product pages
are fetched only after their URL matches a product already present in our
catalogue. ES-100 is skipped because products/images/ES-100.webp already exists.
"""

from __future__ import annotations

import html
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

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


def category_pages() -> list[str]:
    pages: set[str] = set()
    queue = [urljoin(BASE, path) for path in CATEGORY_URLS]

    while queue:
        url = queue.pop(0)
        if url in pages:
            continue
        pages.add(url)

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as exc:
            print(f"CATEGORY ERROR: {url}: {exc}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        base_path = urlparse(url).path

        # Follow pagination links belonging to this same category only.
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            parsed = urlparse(href)
            if parsed.netloc == urlparse(BASE).netloc and parsed.path == base_path:
                if href not in pages and len(pages) < 100:
                    queue.append(href)

    return sorted(pages)


def product_urls() -> list[str]:
    urls: set[str] = set()
    for category_url in category_pages():
        try:
            r = session.get(category_url, timeout=30)
            r.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = urljoin(category_url, a["href"])
            if "/en/product-details/" in href:
                urls.add(href.split("#", 1)[0])
    return sorted(urls)


def score_url(name: str, url: str) -> int:
    u = norm(url.rsplit("/", 1)[-1])
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    strong = [t for t in tokens if any(ch.isdigit() for ch in t)]
    tokens = strong or [t for t in tokens if len(t) >= 4]

    score = sum(1 for token in tokens if norm(token) in u)
    if norm(name) in u:
        score += 20
    return score


def find_url(name: str, urls: list[str]) -> str | None:
    ranked = sorted(((score_url(name, u), u) for u in urls), reverse=True)
    if not ranked:
        return None
    score, url = ranked[0]
    if score < 2 and len(re.findall(r"[a-z0-9]+", name.lower())) > 1:
        return None
    return url


def save_as_webp(data: bytes, output: Path) -> None:
    image = Image.open(BytesIO(data)).convert("RGB")
    image.save(output, "WEBP", quality=88, method=6)


def main() -> int:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    targets = read_targets()
    urls = product_urls()

    print(f"Found {len(urls)} permitted-category product pages.")
    print(f"Matching against {len(targets)} website products.")

    downloaded = skipped = missing = 0

    for slug, name in targets.items():
        if slug in SKIP and (IMAGE_DIR / "ES-100.webp").exists():
            print(f"SKIP existing image: {name}")
            skipped += 1
            continue

        source_url = find_url(name, urls)
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
