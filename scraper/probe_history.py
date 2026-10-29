"""
Test whether nepalstock.com (via the `nepse` library) can return a PAST date.
Prints its findings in the Actions log. Usage: python scraper/probe_history.py 2026-10-28
"""
import inspect
import sys

from nepse import Nepse

day = sys.argv[1] if len(sys.argv) > 1 else "2026-10-27"
n = Nepse()
n.setTLSVerification(False)
print("Floorsheet-related methods:")
for name in dir(n):
    if "loor" in name:
        try:
            print(" ", name, inspect.signature(getattr(n, name)))
        except Exception:
            print(" ", name)

for name in ("getFloorSheetOf", "getFloorSheet"):
    fn = getattr(n, name, None)
    if not fn:
        continue
    for args, kwargs in (
        (("NABIL", day), {}),
        (("NABIL",), {"business_date": day}),
        ((day,), {}),
        ((), {"business_date": day}),
    ):
        try:
            res = fn(*args, **kwargs)
            print(f"TRY {name}{args}{kwargs}: {len(res)} rows;",
                  "first:", res[0] if res else None)
        except Exception as e:  # noqa: BLE001
            print(f"TRY {name}{args}{kwargs}: failed -> {type(e).__name__}: {str(e)[:150]}")
