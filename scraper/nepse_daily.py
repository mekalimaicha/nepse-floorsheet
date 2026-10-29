"""
Daily scrape from nepalstock.com (via the open-source `nepse` library).
This source includes the exact trade time. It returns the LATEST trading day,
so on holidays it simply re-returns the previous day (we detect that and skip).

  python scraper/nepse_daily.py
"""
import sys
from datetime import date, datetime

from nepse import Nepse

import common


def main():
    n = Nepse()
    n.setTLSVerification(False)  # nepalstock's certificate often fails verification
    data = n.getFloorSheet()
    if not data:
        print("No floorsheet data returned; nothing saved.")
        return 0
    recs = []
    for r in data:
        row = {c: r.get(c, "") for c in common.COLUMNS}
        row["contractId"] = str(r.get("contractId", "")).split(".")[0]
        row["tradeDate"], row["tradeClock"] = common.split_time(row["tradeTime"])
        recs.append(row)
    d = date.fromisoformat(str(recs[0]["businessDate"])[:10])
    path = common.OUT_DIR / d.strftime(common.FILENAME_FORMAT)
    if path.exists():
        print(f"{path} already exists (holiday or already scraped); nothing to do.")
        return 0
    common.learn_lookups(recs)
    p = common.save_csv(d, recs)
    print(f"Saved {len(recs)} rows -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
