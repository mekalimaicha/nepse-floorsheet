"""Shared helpers: column list, lookup tables, CSV saving."""
import csv
from datetime import datetime
from pathlib import Path

OUT_DIR = Path("data")
LOOKUP_DIR = OUT_DIR / "lookups"
FILENAME_FORMAT = "%Y-%m-%d_Floorsheet.csv"  # e.g. 2026-10-30_Floorsheet.csv

COLUMNS = [
    "contractId", "stockSymbol", "buyerMemberId", "sellerMemberId",
    "contractQuantity", "contractRate", "contractAmount", "businessDate",
    "tradeBookId", "stockId", "buyerBrokerName", "sellerBrokerName",
    "tradeTime", "securityName",
    # extra columns split out for analysis
    "tradeDate", "tradeClock",
]


def _load(name, key):
    p = LOOKUP_DIR / name
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return {r[key]: r for r in csv.DictReader(f)}


BROKERS = _load("brokers.csv", "memberId")
STOCKS = _load("stocks.csv", "stockSymbol")


def learn_lookups(records):
    """Add any new broker / stock names found in full-detail records to the lookup files."""
    new_b = {r["buyerMemberId"]: r["buyerBrokerName"] for r in records if r.get("buyerBrokerName")}
    new_b.update({r["sellerMemberId"]: r["sellerBrokerName"] for r in records if r.get("sellerBrokerName")})
    new_s = {r["stockSymbol"]: (r["stockId"], r["securityName"]) for r in records if r.get("securityName")}
    changed = False
    for k, v in new_b.items():
        if k not in BROKERS:
            BROKERS[k] = {"memberId": k, "brokerName": v}; changed = True
    for k, (i, n) in new_s.items():
        if k not in STOCKS:
            STOCKS[k] = {"stockSymbol": k, "stockId": i, "securityName": n}; changed = True
    if changed:
        LOOKUP_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOOKUP_DIR / "brokers.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["memberId", "brokerName"])
            for k in sorted(BROKERS, key=lambda x: int(x) if x.isdigit() else 0):
                w.writerow([k, BROKERS[k]["brokerName"]])
        with open(LOOKUP_DIR / "stocks.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["stockSymbol", "stockId", "securityName"])
            for k in sorted(STOCKS):
                w.writerow([k, STOCKS[k]["stockId"], STOCKS[k]["securityName"]])


def split_time(trade_time):
    """'2026-10-28T14:59:59.999526' -> ('2026-10-28', '14:59:59.999526')"""
    if not trade_time:
        return "", ""
    s = str(trade_time).replace(" ", "T")
    d, _, t = s.partition("T")
    return d, t


def save_csv(d, records):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / d.strftime(FILENAME_FORMAT)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    tmp.replace(path)
    return path
