"""
KLS Martin online catalog scraper — Playwright edition, with resume support
=============================================================================

WHY PLAYWRIGHT: the category listing pages (/shop/en/products/<slug>/<n>/)
render their product grid client-side via JavaScript. A plain requests +
BeautifulSoup fetch only sees the raw server HTML, which contains the nav/
breadcrumbs but NO product tiles — so a pure-requests crawler silently
discovers almost no products (confirmed: e.g. 10-100-04-07 is completely
absent from grid-based static HTML, yet the product page itself exists and
is fully server-rendered). Individual product pages ARE fully server-side
rendered, so those are still parsed with plain requests (fast).

Strategy:
1. Discover the category tree from the nav (static HTML, cached once).
2. For each category, launch a headless browser, visit each page
   /shop/en/products/<slug>/<n>/, wait for the grid to render, and pull
   every /shop/en/products/product/<code>/ link from the RENDERED DOM.
   Stop when a page yields no product links. Checkpoint after every
   category.
3. Visit each discovered product URL with plain requests, parse code /
   description / brochures / IFU link, and append to CSV immediately.
   Checkpoint after every product.
4. Re-running the script resumes exactly where it left off.

State is kept in klsmartin_state.json (progress) and klsmartin_products.csv
(results, appended incrementally). Delete both to start completely fresh;
delete just the CSV to re-parse products while keeping the crawled URL list.

Install deps first:
    pip install requests beautifulsoup4 playwright --break-system-packages
    playwright install chromium --with-deps

Usage:
    python klsmartin_scraper.py
    (safe to Ctrl-C and re-run any time)
"""

import csv
import json
import os
import re
import time
import random
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = "https://www.klsmartin.com"
START_URL = f"{BASE}/shop/en/products/1/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
DELAY_RANGE = (1.0, 2.2)          # politeness delay between requests-based fetches
BROWSER_DELAY_RANGE = (1.5, 3.0)  # politeness delay between category page loads
PRODUCT_LINK_RE = re.compile(r"/shop/en/products/product/[^/\"'#]+/?")

STATE_FILE = "klsmartin_state.json"
CSV_FILE = "klsmartin_products.csv"
CSV_FIELDS = ["code", "description", "brochures", "ifu_link", "product_url"]

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------
# State management (resume support)
# --------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {}
    state.setdefault("categories", None)
    state.setdefault("categories_done", [])
    state.setdefault("product_urls", [])
    state.setdefault("processed_urls", [])
    return state


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def ensure_csv_header():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def append_row_to_csv(row):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)


# --------------------------------------------------------------------------
# Fetching helpers (plain requests — used only for individual product pages,
# which ARE server-rendered)
# --------------------------------------------------------------------------

def get(url, retries=3):
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                return resp
            print(f"  [{resp.status_code}] {url}")
        except requests.RequestException as e:
            print(f"  error {e} on {url}")
        time.sleep(2 * (attempt + 1))
    return None


def polite_sleep(rng=DELAY_RANGE):
    time.sleep(random.uniform(*rng))


# --------------------------------------------------------------------------
# Category discovery (static HTML nav is fine for this part)
# --------------------------------------------------------------------------

def discover_category_urls():
    resp = get(START_URL)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    cats = set()
    for a in soup.select("a[href*='/shop/en/products/']"):
        href = a.get("href", "")
        if "/product/" in href:
            continue
        m = re.match(r"^(?:https?://[^/]+)?/shop/en/products/([^/]+)/\d+/", href)
        if m:
            cats.add(m.group(1))
    return sorted(cats)


# --------------------------------------------------------------------------
# Category product-grid crawl (needs a real browser — grid is JS-rendered)
# --------------------------------------------------------------------------

def product_urls_in_category(page, slug):
    """Use an already-open Playwright page to walk a category's paginated grid."""
    urls = set()
    pagenum = 1
    while True:
        url = f"{BASE}/shop/en/products/{slug}/{pagenum}/"
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Give any lazy XHR-driven grid a moment to finish rendering.
            page.wait_for_timeout(800)
        except Exception as e:
            print(f"  browser error on {url}: {e}")
            break

        html = page.content()
        found = set(urljoin(BASE, m) for m in PRODUCT_LINK_RE.findall(html))

        if not found:
            break
        new = found - urls
        urls |= found
        if not new:
            break
        pagenum += 1
        polite_sleep(BROWSER_DELAY_RANGE)
    return urls


# --------------------------------------------------------------------------
# Product page parsing (plain requests — fully server-rendered)
# --------------------------------------------------------------------------

def parse_product(url):
    resp = get(url)
    if not resp:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")

    code_el = soup.select_one("h1")
    code = code_el.get_text(strip=True).replace("Art. No.", "").strip() if code_el else ""

    desc_el = soup.select_one("h2")
    description = desc_el.get_text(strip=True) if desc_el else ""

    brochures = []
    for row in soup.select("tr"):
        header = row.find("th") or row.find_previous("th")
        if row.find(string=re.compile("Brochure", re.I)) or (header and "Brochure" in header.get_text()):
            for a in row.select("a[href$='.pdf']"):
                brochures.append({"name": a.get_text(strip=True), "url": urljoin(BASE, a["href"])})

    if not brochures:
        for a in soup.select("a[href$='.pdf']"):
            brochures.append({"name": a.get_text(strip=True), "url": urljoin(BASE, a["href"])})

    ifu_link = ""
    ifu_a = soup.find("a", string=re.compile("Instructions for use", re.I))
    if ifu_a:
        ifu_link = urljoin(BASE, ifu_a["href"])

    return {
        "code": code,
        "description": description,
        "brochures": "; ".join(f"{b['name']} ({b['url']})" for b in brochures),
        "ifu_link": ifu_link,
        "product_url": url,
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    state = load_state()
    ensure_csv_header()

    # Phase 1: discover categories (once)
    if state["categories"] is None:
        print("Discovering categories...")
        state["categories"] = discover_category_urls()
        save_state(state)
    categories = state["categories"]
    print(f"Categories: {len(categories)} total, {len(state['categories_done'])} already crawled")

    # Phase 2: crawl each category's rendered grid for product URLs
    product_urls = set(state["product_urls"])
    remaining_cats = [c for c in categories if c not in state["categories_done"]]

    if remaining_cats:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = ctx.new_page()
            try:
                for i, slug in enumerate(remaining_cats, 1):
                    print(f"[{i}/{len(remaining_cats)}] category: {slug}")
                    urls = product_urls_in_category(page, slug)
                    print(f"    -> {len(urls)} product links")
                    product_urls |= urls
                    state["product_urls"] = sorted(product_urls)
                    state["categories_done"].append(slug)
                    save_state(state)  # checkpoint after every category
                    polite_sleep(BROWSER_DELAY_RANGE)
            except KeyboardInterrupt:
                print("\nInterrupted during category crawl — progress saved. Re-run to resume.")
                browser.close()
                return
            browser.close()

    print(f"\nTotal unique product URLs discovered: {len(product_urls)}")

    # Phase 3: parse each product page (plain requests, skip already-processed)
    remaining_products = [u for u in sorted(product_urls) if u not in state["processed_urls"]]
    print(f"Remaining products to parse: {len(remaining_products)}")

    try:
        for i, url in enumerate(remaining_products, 1):
            print(f"[{i}/{len(remaining_products)}] parsing {url}")
            data = parse_product(url)
            if data and data["code"]:
                append_row_to_csv(data)
            state["processed_urls"].append(url)
            save_state(state)  # checkpoint after every single product
            polite_sleep()
    except KeyboardInterrupt:
        print("\nInterrupted during product parsing — progress saved. Re-run to resume.")
        return

    print(f"\nDone. Results in {CSV_FILE}")


if __name__ == "__main__":
    main()