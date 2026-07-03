"""
scrape_shares.py
Visits each company's page on sharehubnepal.com and pulls ownership structure
(promoter vs. public shares) plus a few fundamentals (market cap, EPS, P/E,
book value). This data changes rarely, so this runs weekly, not on the
15-min price schedule.

Run manually: python scrape_shares.py
"""

import json
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

from scrape_prices import SECTOR_MAP  # reuse the same symbol list

BASE_URL = "https://sharehubnepal.com/company/{}"
OUTPUT_FILE = "shares.json"
DELAY_SECONDS = 1.5  # be polite between requests across ~194 pages

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def to_number(raw):
    raw = raw.replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def fetch_ownership(symbol):
    url = BASE_URL.format(symbol)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  {symbol}: request failed ({e})", file=sys.stderr)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    result = {}

    m = re.search(r"Promoter Share\s*([\d,]+)\s*\(([\d.]+)%\)", text)
    if m:
        result["promoter_shares"] = to_number(m.group(1))
        result["promoter_pct"] = float(m.group(2))

    m = re.search(r"Public Share\s*([\d,]+)\s*\(([\d.]+)%\)", text)
    if m:
        result["public_shares"] = to_number(m.group(1))
        result["public_pct"] = float(m.group(2))

    m = re.search(r"Total Listed Share\s*([\d,]+)", text)
    if m:
        result["listed_shares"] = to_number(m.group(1))

    m = re.search(r"Market Capitalization\s*Rs\.\s*([\d,]+)", text)
    if m:
        result["market_cap"] = to_number(m.group(1))

    m = re.search(r"Market Capitalization \(Float\)\s*Rs\.\s*([\d,]+)", text)
    if m:
        result["float_market_cap"] = to_number(m.group(1))

    m = re.search(r"\bEPS\s*(-?[\d.]+)", text)
    if m:
        result["eps"] = to_number(m.group(1))

    m = re.search(r"P/E Ratio\s*(-?[\d.]+)", text)
    if m:
        result["pe_ratio"] = to_number(m.group(1))

    m = re.search(r"Book Value\s*(-?[\d.]+)", text)
    if m:
        result["book_value"] = to_number(m.group(1))

    m = re.search(r"\bPBV\s*(-?[\d.]+)", text)
    if m:
        result["pbv"] = to_number(m.group(1))

    if not result:
        print(f"  {symbol}: no ownership/fundamental data found on page", file=sys.stderr)
        return None

    return result


def main():
    symbols = sorted(SECTOR_MAP.keys())
    results = {}

    for i, symbol in enumerate(symbols, 1):
        data = fetch_ownership(symbol)
        if data:
            results[symbol] = data
            pct = data.get("promoter_pct")
            print(f"[{i}/{len(symbols)}] {symbol}: promoter {pct}%" if pct is not None
                  else f"[{i}/{len(symbols)}] {symbol}: partial data")
        else:
            print(f"[{i}/{len(symbols)}] {symbol}: skipped")
        time.sleep(DELAY_SECONDS)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {len(results)}/{len(symbols)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
