"""
Diagnostics for nepalstock access via the NepseUnofficialApi library.
Prints (1) the library's floorsheet code, (2) what happens when we call it,
(3) whether a past date is accepted. Usage: python scraper/probe_history.py 2026-10-27
"""
import inspect
import sys
import traceback

from nepse import Nepse

day = sys.argv[1] if len(sys.argv) > 1 else "2026-10-27"
n = Nepse()
n.setTLSVerification(False)

print("=== Floorsheet-related methods ===")
names = [x for x in dir(n) if "loor" in x]
for name in names:
    try:
        print(" ", name, inspect.signature(getattr(n, name)))
    except Exception:
        print(" ", name)

print("\n=== Library source code of those methods ===")
for name in names:
    try:
        print(f"\n--- {name} ---")
        print(inspect.getsource(getattr(n, name))[:3500])
    except Exception as e:  # noqa: BLE001
        print("  (no source:", e, ")")

print("\n=== API end points ===")
for attr in ("api_end_points", "_api_end_points"):
    if hasattr(n, attr):
        print(getattr(n, attr))

print("\n=== Calls ===")
tests = []
if hasattr(n, "getFloorSheetOf"):
    tests += [("getFloorSheetOf", ("NABIL", day), {}),
              ("getFloorSheetOf", ("NABIL",), {"business_date": day})]
tests += [("getFloorSheet", (), {}), ("getFloorSheet", (), {"business_date": day})]
for name, args, kwargs in tests:
    fn = getattr(n, name, None)
    if not fn:
        continue
    try:
        res = fn(*args, **kwargs)
        print(f"OK {name}{args}{kwargs}: {len(res)} rows; first: {res[0] if res else None}")
    except Exception:  # noqa: BLE001
        print(f"FAILED {name}{args}{kwargs}")
        traceback.print_exc(limit=3)
