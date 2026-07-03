"""
scrape_prices.py
Scrapes sharesansar.com's Today Share Price table, joins each symbol with a
static sector map, and writes prices.json for the NEPSE screener to consume.

Run manually:   python scrape_prices.py
Run on schedule: see .github/workflows/update-prices.yml
"""

import json
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URL = "https://www.sharesansar.com/today-share-price"
OUTPUT_FILE = "prices.json"

# Static sector map — sector classification barely changes, so this is
# maintained by hand. Add new listings here as they IPO.
SECTOR_MAP = {
    # Commercial Bank
    "ADBL": "Commercial Bank", "CZBIL": "Commercial Bank", "EBL": "Commercial Bank",
    "GBIME": "Commercial Bank", "HBL": "Commercial Bank", "KBL": "Commercial Bank",
    "NABIL": "Commercial Bank", "NBL": "Commercial Bank", "NICA": "Commercial Bank",
    "NIMB": "Commercial Bank", "NMB": "Commercial Bank", "PCBL": "Commercial Bank",
    "PRVU": "Commercial Bank", "SANIMA": "Commercial Bank", "SBI": "Commercial Bank",
    "SBL": "Commercial Bank", "SCB": "Commercial Bank",

    # Development Bank
    "EDBL": "Development Bank", "GBBL": "Development Bank", "GRDBL": "Development Bank",
    "JBBL": "Development Bank", "LBBL": "Development Bank", "MDB": "Development Bank",
    "MLBL": "Development Bank", "MNBBL": "Development Bank", "NABBC": "Development Bank",
    "SADBL": "Development Bank", "SHINE": "Development Bank", "SINDU": "Development Bank",

    # Finance
    "BFC": "Finance", "CFCL": "Finance", "GFCL": "Finance", "GMFIL": "Finance",
    "GUFL": "Finance", "ICFC": "Finance", "JFL": "Finance", "MPFL": "Finance",
    "NFS": "Finance", "PFL": "Finance", "PROFL": "Finance", "RLFL": "Finance",
    "SFCL": "Finance", "SIFC": "Finance",

    # Microfinance
    "ACLBSL": "Microfinance", "ALBSL": "Microfinance", "ANLB": "Microfinance",
    "AVYAN": "Microfinance", "CBBL": "Microfinance", "CYCL": "Microfinance",
    "DDBL": "Microfinance", "DLBS": "Microfinance", "FMDBL": "Microfinance",
    "FOWAD": "Microfinance", "GBLBS": "Microfinance", "GILB": "Microfinance",
    "GLBSL": "Microfinance", "GMFBS": "Microfinance", "HLBSL": "Microfinance",
    "ILBS": "Microfinance", "JBLB": "Microfinance", "JSLBB": "Microfinance",
    "KMCDB": "Microfinance", "LLBS": "Microfinance", "MATRI": "Microfinance",
    "MERO": "Microfinance", "MLBBL": "Microfinance", "MLBS": "Microfinance",
    "MLBSL": "Microfinance", "MSLB": "Microfinance", "NADEP": "Microfinance",
    "NESDO": "Microfinance", "NMBMF": "Microfinance", "NMFBS": "Microfinance",
    "NUBL": "Microfinance", "RSDC": "Microfinance",

    # Life Insurance
    "ALICL": "Life Insurance", "CLI": "Life Insurance", "GMLI": "Life Insurance",
    "HLI": "Life Insurance", "ILI": "Life Insurance", "LICN": "Life Insurance",
    "NLIC": "Life Insurance", "NLICL": "Life Insurance", "RNLI": "Life Insurance",
    "SJLIC": "Life Insurance", "SNLI": "Life Insurance", "SRLI": "Life Insurance",

    # Non-Life Insurance
    "HEI": "Non-Life Insurance", "IGI": "Non-Life Insurance", "NICL": "Non-Life Insurance",
    "NIL": "Non-Life Insurance", "NLG": "Non-Life Insurance", "NRIC": "Non-Life Insurance",
    "PRIN": "Non-Life Insurance", "SALICO": "Non-Life Insurance", "SGIC": "Non-Life Insurance",
    "SICL": "Non-Life Insurance", "SPIL": "Non-Life Insurance",

    # Hydropower
    "AHL": "Hydropower", "AHPC": "Hydropower", "AKJCL": "Hydropower", "AKPL": "Hydropower",
    "APHL": "Hydropower", "BARUN": "Hydropower", "BEDC": "Hydropower", "BGWT": "Hydropower",
    "BHCL": "Hydropower", "BHDC": "Hydropower", "BHL": "Hydropower", "BHPL": "Hydropower",
    "BJHL": "Hydropower", "BNHC": "Hydropower", "BPCL": "Hydropower", "BUNGAL": "Hydropower",
    "CHCL": "Hydropower", "CHL": "Hydropower", "DHEL": "Hydropower", "DHPL": "Hydropower",
    "DOLTI": "Hydropower", "DORDI": "Hydropower", "EHPL": "Hydropower", "GHL": "Hydropower",
    "GLH": "Hydropower", "HDHPC": "Hydropower", "HPPL": "Hydropower", "HURJA": "Hydropower",
    "IHL": "Hydropower", "KHPL": "Hydropower", "KKHC": "Hydropower", "KPCL": "Hydropower",
    "LEC": "Hydropower", "MABEL": "Hydropower", "MAKAR": "Hydropower", "MANDU": "Hydropower",
    "MBJC": "Hydropower", "MCHL": "Hydropower", "MEHL": "Hydropower", "MEL": "Hydropower",
    "MEN": "Hydropower", "MHCL": "Hydropower", "MHL": "Hydropower", "MHNL": "Hydropower",
    "MKHC": "Hydropower", "MKHL": "Hydropower", "MKJC": "Hydropower", "MMKJL": "Hydropower",
    "NGPL": "Hydropower", "NHDL": "Hydropower", "NHPC": "Hydropower", "NYADI": "Hydropower",
    "PHCL": "Hydropower", "PMHPL": "Hydropower", "PPCL": "Hydropower", "PPL": "Hydropower",
    "RADHI": "Hydropower", "RAWA": "Hydropower", "RFPL": "Hydropower", "RHGCL": "Hydropower",
    "RHPL": "Hydropower", "RIDI": "Hydropower", "RLEL": "Hydropower",

    # Hotel & Tourism
    "BANDIPUR": "Hotel & Tourism", "CGH": "Hotel & Tourism", "CITY": "Hotel & Tourism",
    "HFIN": "Hotel & Tourism", "KDL": "Hotel & Tourism", "OHL": "Hotel & Tourism",
    "SHL": "Hotel & Tourism",

    # Manufacturing & Processing
    "BNL": "Manufacturing & Processing", "GCIL": "Manufacturing & Processing",
    "OMPL": "Manufacturing & Processing", "PCIL": "Manufacturing & Processing",
    "RSML": "Manufacturing & Processing", "SHIVM": "Manufacturing & Processing",
    "SARBTM": "Manufacturing & Processing", "SAIL": "Manufacturing & Processing",
    "SONA": "Manufacturing & Processing", "SYPNL": "Manufacturing & Processing",
    "UNL": "Manufacturing & Processing", "BNT": "Manufacturing & Processing",

    # Investment
    "CHDC": "Investment", "CIT": "Investment", "ENL": "Investment", "HATHY": "Investment",
    "HIDCL": "Investment", "NIFRA": "Investment", "NRN": "Investment",

    # Others
    "HRL": "Others", "JHAPA": "Others", "MKCL": "Others", "NRM": "Others",
    "NWCL": "Others", "PURE": "Others",

    # Trading
    "BBC": "Trading", "STC": "Trading",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch_prices():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the table that actually has "Symbol" and "LTP" headers rather than
    # guessing an id/class, since markup can change.
    table = None
    for t in soup.find_all("table"):
        header_text = t.get_text(" ", strip=True).lower()
        if "symbol" in header_text and "ltp" in header_text:
            table = t
            break
    if table is None:
        print("Could not find price table on page", file=sys.stderr)
        sys.exit(1)

    header_row = table.find("tr")
    headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
    try:
        symbol_idx = next(i for i, h in enumerate(headers) if "symbol" in h)
        ltp_idx = next(i for i, h in enumerate(headers) if h == "ltp" or "ltp" in h)
    except StopIteration:
        print("Could not locate Symbol/LTP columns in header row", file=sys.stderr)
        sys.exit(1)

    records = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) <= max(symbol_idx, ltp_idx):
            continue
        symbol = cells[symbol_idx].upper().strip()
        ltp_raw = cells[ltp_idx].replace(",", "")
        if not re.match(r"^-?\d+(\.\d+)?$", ltp_raw):
            continue
        ltp = float(ltp_raw)

        sector = SECTOR_MAP.get(symbol)
        if sector is None:
            continue  # skip debentures, bonds, mutual funds, unmapped symbols

        records.append({"symbol": symbol, "sector": sector, "ltp": ltp})

    return records


def main():
    records = fetch_prices()
    if not records:
        print("No records scraped — site structure may have changed.", file=sys.stderr)
        sys.exit(1)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "prices": records,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(records)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
