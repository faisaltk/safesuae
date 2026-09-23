#!/usr/bin/env python3
"""
Download permitted SafeOne product images for the ZEN GROUP catalogue.

This script reads the product names already used by the website, finds matching
SafeOne product-detail URLs from the public sitemap, downloads only those
matching product pages, extracts the OpenGraph main image, and saves it as
products/images/<our-slug>.webp (or .jpg/.png when WebP is unavailable).

ES-100 is intentionally skipped because the repository already contains it.
"""

from __future__ import annotations

import html
import re
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://www.safeoneuae.com"
SITEMAP = f"{BASE}/sitemap.xml"
PRODUCT_FILE = Path("products/product-detail.html")
IMAGE_DIR = Path("products/images")
SKIP = {"eagle-es-100"}
HEADERS = {"User-Agent": "ZEN-GROUP-product-image-import/1.0"}

session = requests.Session()
session.headers.update(HEADERS)


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def read_targets() -> dict[str, str]:
    text = PRODUCT_FILE.read_text(encoding="utf-8")
    pairs = re.findall(r'{"slug":"([^"]+)","name":"([^"]+)"', text)
    return {slug: html.unescape(name) for slug, name in pairs}


def sitemap_urls() -> list[str]:
    r = session.get(SITEMAP, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    return [
        loc.get_text(strip=True)
        for loc in soup.find_all("loc")
        if "/en/product-details/" in loc.get_text()
    ]


def target_tokens(name: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    # Model numbers are the strongest match. Otherwise use the meaningful words.
    strong = [t for t in tokens if any(ch.isdigit() for ch in t)]
    return strong or [t for t in tokens if len(t) >= 4]


def score_url(name: str, url: str) -> int:
    u = norm(url.rsplit("/", 1)[-1])
    tokens = target_tokens(name)
    score = sum(1 for t in tokens if norm(t) in u)

    # Brand + distinctive model/name is a strong match.
    n = norm(name)
    if n and n in u:
        score += 20
    return score


def find_url(name: str, urls: list[str]) -> str | None:
    scored = sorted(((score_url(name, u), u) for u in urls), reverse=True)
    if not scored or scored[0][0] < 1:
        return None
    best_score, best_url = scored[0]
    # Avoid weak accidental matches for generic storage names.
    if best_score < 2 and len(target_tokens(name)) > 1:
        return None
    return best_url


def main() -> int:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    targets = read_targets()
    urls = sitemap_urls()
    print(f"Found {len(urls)} SafeOne product-detail URLs.")
    print(f"Website catalogue contains {len(targets)} products.")

    downloaded = 0
    skipped = 0
    missing = 0

    for slug, name in targets.items():
        if slug in SKIP:
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
            for selector in [
                ('meta', {'property': 'og:image'}),
                ('meta', {'name': 'twitter:image'}),
            ]:
                tag = soup.find(*selector)
                if tag and tag.get("content"):
                    image_url = urljoin(source_url, tag["content"])
                    break

            if not image_url:
                # Fallback: choose a product-looking image from the page.
                for img in soup.find_all("img"):
                    src = img.get("src") or img.get("data-src")
                    if src and "logo" not in src.lower() and "whatsapp" not in src.lower():
                        image_url = urljoin(source_url, src)
                        break

            if not image_url:
                print(f"NO IMAGE: {name}")
                missing += 1
                continue

            img = session.get(image_url, timeout=30)
            img.raise_for_status()

            content_type = (img.headers.get("Content-Type") or "").lower()
            if "webp" in content_type:
                ext = ".webp"
            elif "png" in content_type:
                ext = ".png"
            else:
                ext = ".jpg"

            # Prefer WebP for the site's catalogue when the source is WebP.
            out = IMAGE_DIR / f"{slug}{ext}"
            out.write_bytes(img.content)
            print(f"OK: {name} -> {out}")
            downloaded += 1
            time.sleep(0.25)

        except Exception as exc:
            print(f"ERROR: {name}: {exc}")
            missing += 1

    print()
    print(f"Downloaded: {downloaded}")
    print(f"Skipped existing: {skipped}")
    print(f"Missing/errors: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
