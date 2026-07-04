"""
scrape_shares.py
Visits each company's page on nepsealpha.com and pulls the ownership
breakdown (Promoter / Public / Locked holding) plus market cap.

IMPORTANT: nepsealpha.com renders this data with client-side JavaScript —
a plain `requests.get()` returns an almost-empty page. This script uses
Playwright (a headless browser) to actually render the page first, the same
way your own browser does, then reads the real numbers out of it.

This data changes rarely, so this runs weekly, not on the 15-min price
schedule.

Setup (once): pip install playwright && playwright install --with-deps chromium
Run manually: python scrape_shares.py
"""

import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

from scrape_prices import SECTOR_MAP  # reuse the same symbol list

BASE_URL = "https://nepsealpha.com/stocks/{}/info"
OUTPUT_FILE = "shares.json"
DELAY_SECONDS = 1.0  # be polite between requests across ~194 pages


def to_number(raw):
    raw = raw.replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def parse_holding(text, label):
    """Matches e.g. 'Promoter Holding 51.00% / 79,100,011.89 Nos'."""
    m = re.search(
        rf"{label}\s*([\d.]+)\s*%\s*/\s*([\d,]+\.?\d*)\s*Nos",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None, None
    return to_number(m.group(1)), to_number(m.group(2))


def fetch_ownership(page, symbol):
    url = BASE_URL.format(symbol)
    try:
        # domcontentloaded is fast and reliable; networkidle hangs on sites
        # with continuous background polling (ads, live-price tickers, etc.)
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            # Wait specifically for the content we need rather than the
            # whole network going quiet — much faster and more reliable.
            page.wait_for_selector("text=Promoter Holding", timeout=12000)
        except Exception:
            pass  # fall through and read whatever did render
        text = page.inner_text("body")
    except Exception as e:
        print(f"  {symbol}: page load failed ({e})", file=sys.stderr)
        return None

    result = {}

    promoter_pct, promoter_nos = parse_holding(text, "Promoter Holding")
    if promoter_pct is not None:
        result["promoter_pct"] = promoter_pct
        result["promoter_shares"] = promoter_nos

    public_pct, public_nos = parse_holding(text, "Public Holding")
    if public_pct is not None:
        result["public_pct"] = public_pct
        result["public_shares"] = public_nos

    locked_pct, locked_nos = parse_holding(text, "Locked Holding")
    if locked_pct is not None:
        result["locked_pct"] = locked_pct
        result["locked_shares"] = locked_nos

    if promoter_nos is not None or public_nos is not None or locked_nos is not None:
        result["listed_shares"] = round(
            (promoter_nos or 0) + (public_nos or 0) + (locked_nos or 0), 2
        )

    m = re.search(r"Market\s*Cap(?:italization)?[:\s]*(?:Rs\.?)?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    if m:
        result["market_cap_snapshot"] = to_number(m.group(1))

    m = re.search(r"\bEPS\b[:\s]*(-?[\d.]+)", text)
    if m:
        result["eps"] = to_number(m.group(1))

    m = re.search(r"P\s*/\s*E\s*(?:Ratio)?[:\s]*(-?[\d.]+)", text, re.IGNORECASE)
    if m:
        result["pe_ratio"] = to_number(m.group(1))

    if not result:
        print(f"  {symbol}: no ownership/fundamental data found on page", file=sys.stderr)
        return None

    return result


def main():
    symbols = sorted(SECTOR_MAP.keys())
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for i, symbol in enumerate(symbols, 1):
            data = fetch_ownership(page, symbol)
            if data:
                results[symbol] = data
                pct = data.get("promoter_pct")
                print(f"[{i}/{len(symbols)}] {symbol}: promoter {pct}%" if pct is not None
                      else f"[{i}/{len(symbols)}] {symbol}: partial data")
            else:
                print(f"[{i}/{len(symbols)}] {symbol}: skipped")
            time.sleep(DELAY_SECONDS)

        browser.close()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {len(results)}/{len(symbols)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
