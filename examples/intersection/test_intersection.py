"""Scan-simulator checks for FB_Intersection.

    PYTHONPATH=<codesys-lad>/scripts python test_intersection.py Project.xml
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "codesys-lad" / "scripts"))
from ld_sim import Sim  # noqa: E402

ST = ["AllRedToNS", "GreenNS", "YellowNS", "AllRedToEW", "GreenEW", "YellowEW", "Faulted"]
failures = []
safety = []


def check(name, ok, detail=""):
    print("PASS" if ok else "FAIL", name, detail)
    if not ok:
        failures.append(name)


def run(s, ms, **inputs):
    """Run ms; return [(time, state)] on each change; lamp safety checked every scan."""
    s.v.update(inputs)
    log, last = [], ST[s.v["_eState"]] if s.v["_eState"] < len(ST) else s.v["_eState"]
    for _ in range(ms // s.dt):
        s.scan()
        ns = s.v["bYellowNS"] or s.v["bGreenNS"]
        ew = s.v["bYellowEW"] or s.v["bGreenEW"]
        if ns and ew:
            safety.append(f"{s.now} ms: conflicting NS/EW")
        n = s.v["_eState"]
        cur = ST[n] if n < len(ST) else n
        if cur != last:
            log.append((s.now, cur))
            last = cur
    return log


s = Sim(sys.argv[1], "FB_Intersection", scan_ms=10)
log = run(s, 40000)
names = [x for _, x in log]
check("1 cycle order", names[:6] == ["GreenNS", "YellowNS", "AllRedToEW", "GreenEW", "YellowEW", "AllRedToNS"], names[:6])
t = dict((n, tm) for tm, n in log)
check("2 times (2s red, 10s green, 3s yellow)", abs((log[1][0] - log[0][0]) - 10000) < 100 and abs((log[2][0] - log[1][0]) - 3000) < 100
      and abs((log[3][0] - log[2][0]) - 2000) < 100, [tm for tm, _ in log[:4]])

s = Sim(sys.argv[1], "FB_Intersection", scan_ms=10)
run(s, 5000)
log = run(s, 100, bFault=True)
check("3 fault trips at once", [x for _, x in log] == ["Faulted"], log)
on = off = 0
for _ in range(200):
    s.scan()
    on += s.v["bRedNS"] and s.v["bRedEW"]
    off += not (s.v["bRedNS"] or s.v["bRedEW"])
    assert not (s.v["bGreenNS"] or s.v["bYellowNS"] or s.v["bGreenEW"] or s.v["bYellowEW"])
check("4 faulted flashes both reds, no green/yellow", on > 50 and off > 50, f"lit {on} dark {off} scans")
log = run(s, 200, bReset=True)
check("5 reset ignored while fault present", log == [], log)
s.v["bReset"] = False
run(s, 50)
s.v["bFault"] = False
log = run(s, 100)
check("6 no reset press, stays faulted", log == [], log)
log = run(s, 100, bReset=True)
check("7 reset after fault clears -> AllRedToNS", [x for _, x in log][:1] == ["AllRedToNS"], log)

s = Sim(sys.argv[1], "FB_Intersection", scan_ms=10)
run(s, 100)
s.v["_eState"] = 42
log = run(s, 100)
check("8 invalid state -> AllRedToNS", [x for _, x in log][:1] == ["AllRedToNS"], log)

check("9 never green/yellow both ways", not safety, safety[:3])
sys.exit(1 if failures else 0)
