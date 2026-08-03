"""
KLS Martin online catalog scraper — with resume support
=========================================================

Strategy (no brute-forcing of xx-xxx-xx-xx codes):

1. Discover the category tree from the nav (once, cached in state file).
2. For each category slug, walk pages /shop/en/products/<slug>/<n>/ until a
   page returns zero product links. Each finished category is checkpointed.
3. Collect every unique product URL (/shop/en/products/product/<code>/).
4. Visit each product page once, parse code / description / brochures / IFU.
   Each parsed product is written to CSV immediately and checkpointed, so a
   crash or Ctrl-C never loses more than the single in-flight request.
5. Re-running the script picks up exactly where it left off — it will not
   re-crawl finished categories or re-parse already-saved products.

State is kept in klsmartin_state.json (progress) and klsmartin_products.csv
(results, appended incrementally). Delete both files to start completely
fresh; delete just the CSV to re-parse products while keeping the crawled
URL list.

Install deps first:
    pip install requests beautifulsoup4 --break-system-packages

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

BASE = "https://www.klsmartin.com"
START_URL = f"{BASE}/shop/en/products/1/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
DELAY_RANGE = (1.0, 2.2)  # be polite / avoid tripping Cloudflare bot protection

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
    state.setdefault("categories", None)          # list of slugs, or None = not discovered yet
    state.setdefault("categories_done", [])        # slugs fully crawled for product urls
    state.setdefault("product_urls", [])           # all discovered product urls
    state.setdefault("processed_urls", [])         # product urls already parsed + written to CSV
    return state


def save_state(state):
    # atomic write so a crash mid-write can't corrupt the state file
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def load_processed_codes_from_csv():
    """In case the CSV has rows the state file doesn't know about (e.g. manual edits)."""
    codes = set()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                codes.add(row["code"])
    return codes


def ensure_csv_header():
    new_file = not os.path.exists(CSV_FILE)
    if new_file:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()


def append_row_to_csv(row):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row)


# --------------------------------------------------------------------------
# Fetching helpers
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


def polite_sleep():
    time.sleep(random.uniform(*DELAY_RANGE))


# --------------------------------------------------------------------------
# Crawling
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


def product_urls_in_category(slug):
    urls = set()
    page = 1
    while True:
        url = f"{BASE}/shop/en/products/{slug}/{page}/"
        resp = get(url)
        if not resp:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        found = {urljoin(BASE, a["href"]) for a in soup.select("a[href*='/shop/en/products/product/']")}
        if not found:
            break
        new = found - urls
        urls |= found
        if not new:
            break
        page += 1
        polite_sleep()
    return urls


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

    # Phase 2: crawl each category for product URLs (skip ones already done)
    product_urls = set(state["product_urls"])
    remaining_cats = [c for c in categories if c not in state["categories_done"]]
    try:
        for i, slug in enumerate(remaining_cats, 1):
            print(f"[{i}/{len(remaining_cats)}] category: {slug}")
            urls = product_urls_in_category(slug)
            print(f"    -> {len(urls)} product links")
            product_urls |= urls
            state["product_urls"] = sorted(product_urls)
            state["categories_done"].append(slug)
            save_state(state)  # checkpoint after every category
            polite_sleep()
    except KeyboardInterrupt:
        print("\nInterrupted during category crawl — progress saved. Re-run to resume.")
        return

    print(f"\nTotal unique product URLs discovered: {len(product_urls)}")

    # Phase 3: parse each product page (skip ones already processed)
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