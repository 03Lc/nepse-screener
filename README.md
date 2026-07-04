# 📈 NEPSE Screener

A live sector-wise stock screener for the Nepal Stock Exchange — find the cheapest stocks by price or market cap, per sector, updated automatically.

**[Live demo →](#)**

## Features

- 🔴 **Live prices** — scraped every 15 min during NEPSE trading hours (Sun–Thu, 11:00–15:00 NPT)
- 🏦 **Sector-wise breakdown** — Commercial Banks, Hydropower, Microfinance, Insurance, and more
- 💰 **Sort by lowest price or lowest market cap**
- 📊 **Click any stock** for listed shares, market cap, and promoter/public ownership split
- ⚙️ Fully automated via GitHub Actions — no server required

## How it works

| File | Purpose |
|---|---|
| `scrape_prices.py` | Pulls today's prices from ShareSansar, tags each stock by sector |
| `scrape_shares.py` | Pulls ownership structure (promoter/public/locked %) and market cap from NepseAlpha, via headless browser |
| `update-prices.yml` | GitHub Action — runs the price scraper every 15 min |
| `update-shares.yml` | GitHub Action — runs the ownership scraper weekly |
| `prices.json` / `shares.json` | Auto-generated data, committed by the Actions above |
| `nepse-screener.html` | The screener itself — fetches `prices.json` live, no backend needed |

## Setup

1. Fork this repo.
2. Enable GitHub Actions (Actions tab → enable workflows).
3. Run both workflows once manually to seed the data.
4. Open `nepse-screener.html` — it points at this repo's raw `prices.json` automatically.

## Disclaimer

Price and ownership data are for informational screening only — not investment advice. Data may lag live NEPSE prices; always verify before trading. Not affiliated with NEPSE, ShareSansar, or NepseAlpha.
