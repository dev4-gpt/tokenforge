"""Fresh tests, run ONCE: baseline vs final champion on the held-out split (never used while optimizing).

    python heldout.py            # refuses to run twice
    python heldout.py --force    # reruns, and records that it was forced
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from tokenforge import harness

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "heldout.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if OUT.exists() and not a.force:
        sys.exit(f"{OUT} already exists; the held-out test is run once. Use --force to rerun (recorded).")

    held = json.loads((ROOT / "splits.json").read_text())["heldout"]
    digest = hashlib.sha256(json.dumps(held, sort_keys=True).encode()).hexdigest()
    committed = (ROOT / "HELDOUT_HASH.txt").read_text().strip()
    if digest != committed:
        sys.exit(f"held-out split changed after it was committed ({digest} != {committed})")

    runs = sorted((ROOT / "results").glob("r-*.json"))
    if not runs:
        sys.exit("no evolve run found in results/")
    run = json.loads(runs[-1].read_text())
    items = harness.load_splits()["heldout"]
    harness.build_reference(items)

    base = harness.evaluate(harness.BASELINE_KERNEL, items)
    champ = harness.evaluate(run["champion_code"], items)
    omp = harness.evaluate(harness.BASELINE_KERNEL, items, omp=True)
    if champ.status != "ok":
        print(f"champion FAILED held-out: {champ.status} {champ.error_snippet}")
    rows = []
    for i, it in enumerate(items):
        b = base.tps[i] if base.tps else 0.0
        c = champ.tps[i] if champ.tps else 0.0
        o = omp.tps[i] if omp.tps else 0.0
        rows.append({"model": it.model, "prompt": it.prompt, "baseline_tps": b, "champion_tps": c,
                     "omp_tps": o, "speedup": c / b if b else 0.0})
        print(f"{it.model:<16} {b:8.1f} -> {c:8.1f} tok/s  ({c / b if b else 0:.2f}x)  [upstream OpenMP {o:.1f}]")
    result = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "run_file": runs[-1].name,
              "hash": digest, "champion_status": champ.status, "items": rows,
              "speedup_geomean": harness.speedup(champ, base),
              "omp_reference_geomean": harness.speedup(omp, base), "forced": a.force}
    OUT.write_text(json.dumps(result, indent=1))
    print(f"held-out speedup (geomean): {result['speedup_geomean']:.2f}x  -> {OUT}")


if __name__ == "__main__":
    main()
