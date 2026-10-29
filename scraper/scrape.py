"""
Merolagani Floorsheet scraper.

Modes
  python scraper/scrape.py daily                  -> today's floorsheet (Nepal date)
  python scraper/scrape.py daily --date 2026-10-29 -> one specific date
  python scraper/scrape.py backfill --budget-minutes 320
        -> walks forward from the last completed date (start: 2014-05-05),
           stops cleanly when the time budget is used up.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

import common

# ----------------------------- SETTINGS ---------------------------------
URL = "https://merolagani.com/Floorsheet.aspx"
OUT_DIR = common.OUT_DIR
STATE_FILE = Path("state/backfill_state.json")
BACKFILL_START = date(2014, 5, 5)
SKIP_WEEKDAYS = {5}                            # 5 = Saturday (Mon=0 ... Sun=6)
NPT = timezone(timedelta(hours=5, minutes=45))  # Nepal time
DELAY_RANGE = (1.0, 2.5)                       # polite pause between pages (seconds)
MAX_ATTEMPTS = 3

COLUMNS = common.COLUMNS
# ------------------------------------------------------------------------

ROWS_JS = """
() => [...document.querySelectorAll('table tr')]
  .map(tr => [...tr.querySelectorAll('td')].map(td => td.innerText.trim()))
  .filter(c => c.length >= 8)
"""

FIRST_TXN_CHANGED_JS = """
prev => {
  const r = [...document.querySelectorAll('table tr')]
    .find(tr => tr.querySelectorAll('td').length >= 8);
  return r && r.querySelectorAll('td')[1].innerText.trim() !== prev;
}
"""


def log(msg):
    print(f"[{datetime.now(NPT):%Y-%m-%d %H:%M:%S} NPT] {msg}", flush=True)


def num(text):
    return text.replace(",", "").strip()


def to_record(cells, d):
    # cells: [#, Transact No, Symbol, Buyer, Seller, Quantity, Rate, Amount]
    cid = cells[1].split(".")[0]
    sym, buy, sell = cells[2], cells[3], cells[4]
    stock = common.STOCKS.get(sym, {})
    return {
        "contractId": cid,
        "stockSymbol": sym,
        "buyerMemberId": buy,
        "sellerMemberId": sell,
        "contractQuantity": num(cells[5]),
        "contractRate": num(cells[6]),
        "contractAmount": num(cells[7]),
        "businessDate": d.isoformat(),
        "tradeBookId": "",                       # not on Merolagani
        "stockId": stock.get("stockId", ""),
        "buyerBrokerName": common.BROKERS.get(buy, {}).get("brokerName", ""),
        "sellerBrokerName": common.BROKERS.get(sell, {}).get("brokerName", ""),
        "tradeTime": "",                         # Merolagani has no time
        "securityName": stock.get("securityName", ""),
        # date = first 8 digits of the contract number (YYYYMMDD)
        "tradeDate": f"{cid[:4]}-{cid[4:6]}-{cid[6:8]}" if len(cid) >= 8 else d.isoformat(),
        "tradeClock": "",
    }


def scrape_date(page, d):
    """Return list of records for date d ([] if the site has no data for it)."""
    page.goto(URL, wait_until="domcontentloaded", timeout=90000)
    page.locator('input[id*="FloorsheetDate"]').first.fill(d.strftime("%m/%d/%Y"))
    page.locator(
        'a[id*="SearchFloorsheet"], input[id*="SearchFloorsheet"], '
        'button:has-text("Search"), a:has-text("Search")'
    ).first.click()
    page.wait_for_load_state("networkidle", timeout=90000)

    body = page.inner_text("body")
    as_of = re.search(r"As of\s+(\d{4})/(\d{2})/(\d{2})", body)
    total = re.search(r"of\s+([\d,]+)\s+records", body)
    if not as_of or not total:
        return []                                   # no data for this date
    shown = date(int(as_of[1]), int(as_of[2]), int(as_of[3]))
    if shown != d:
        return []                                   # site showed a different date
    total_records = int(total[1].replace(",", ""))
    if total_records == 0:
        return []
    pages_m = re.search(r"Total pages:\s*(\d+)", body)
    total_pages = int(pages_m[1]) if pages_m else 1

    records = [to_record(c, d) for c in page.evaluate(ROWS_JS)]
    for n in range(2, total_pages + 1):
        time.sleep(random.uniform(*DELAY_RANGE))
        prev = page.evaluate(ROWS_JS)[0][1]
        page.get_by_role("link", name="Next", exact=True).first.click()
        page.wait_for_function(FIRST_TXN_CHANGED_JS, arg=prev, timeout=90000)
        page.wait_for_load_state("networkidle", timeout=90000)
        records += [to_record(c, d) for c in page.evaluate(ROWS_JS)]
        log(f"  {d} page {n}/{total_pages} ({len(records)}/{total_records})")

    if len(records) != total_records:
        raise RuntimeError(f"{d}: expected {total_records} rows, got {len(records)}")
    return records


def save_csv(d, records):
    return common.save_csv(d, records)


def scrape_with_retry(browser, d):
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        try:
            return scrape_date(page, d)
        except Exception as e:  # noqa: BLE001
            last = e
            log(f"  attempt {attempt}/{MAX_ATTEMPTS} failed for {d}: {e}")
            time.sleep(10 * attempt)
        finally:
            ctx.close()
    raise last


def process_date(browser, d):
    if d.weekday() in SKIP_WEEKDAYS:
        log(f"{d}: Saturday, skipped")
        return
    recs = scrape_with_retry(browser, d)
    if not recs:
        log(f"{d}: no data, skipped")
        return
    path = save_csv(d, recs)
    log(f"{d}: saved {len(recs)} rows -> {path}")


def load_state():
    if STATE_FILE.exists():
        return date.fromisoformat(json.loads(STATE_FILE.read_text())["last_completed"])
    return BACKFILL_START - timedelta(days=1)


def save_state(d):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_completed": d.isoformat()}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["daily", "backfill"])
    ap.add_argument("--date", help="YYYY-MM-DD (daily mode only)")
    ap.add_argument("--budget-minutes", type=float, default=320)
    args = ap.parse_args()

    started = time.time()
    today = datetime.now(NPT).date()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            if args.mode == "daily":
                d = date.fromisoformat(args.date) if args.date else today
                process_date(browser, d)
            else:
                d = load_state() + timedelta(days=1)
                while d <= today:
                    if (time.time() - started) / 60 > args.budget_minutes:
                        log("Time budget used up; will continue next run.")
                        break
                    process_date(browser, d)
                    save_state(d)
                    d += timedelta(days=1)
                else:
                    log("Backfill complete: all dates up to today are done.")
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
