"""Build docs/index.html: a self-contained results page generated from the real result files.

    python scripts/build_report.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from tokenforge.memory import Memory  # noqa: E402

TEMPLATE = ROOT / "scripts" / "report_template.html"
OUT = ROOT / "docs" / "index.html"


def clean(s: str) -> str:
    return re.sub(r"/\S*/(kernel\.c|run_tf\.c):", r"\1:", s or "")[:220]


def main() -> None:
    run_path = sorted((ROOT / "results").glob("r-*.json"))[-1]
    run = json.loads(run_path.read_text())
    held = json.loads((ROOT / "results" / "heldout.json").read_text())
    mem = Memory()
    docs = mem.all(run["run_id"])
    memory = "MongoDB Atlas Vector Search" if docs and mem.col is not None else "local JSONL"
    if not docs:
        jl = ROOT / "results" / "candidates.jsonl"
        docs = [d for d in map(json.loads, jl.read_text().splitlines()) if d.get("run_id") == run["run_id"]]
    cands = [{"round": d["round"], "agent": d["agent"], "mode": (d.get("model") or "").split("/")[-1],
              "status": d["status"], "speedup": round(d.get("dev_speedup") or 0, 3),
              "val": round(d["val_speedup"], 3) if d.get("val_speedup") else None,
              "note": d.get("note") or "", "error": clean(d.get("error_snippet") or ""),
              "promoted": bool(d.get("promoted")), "tokens": d.get("llm_tokens") or 0} for d in docs]
    data = {
        "run_id": run["run_id"], "model": run["models"][0] if run["models"] else "",
        "baseline": run["baseline"], "omp_dev": run["reference_omp"]["dev_speedup"],
        "rounds": [{k: r.get(k) for k in ("round", "champion_dev_speedup", "best_dev_speedup", "n_ok",
                                          "n_total", "promoted_model", "llm_tokens")} for r in run["rounds"]],
        "candidates": cands, "heldout": held, "memory": memory,
        "baseline_code": (ROOT / "kernels" / "baseline.c").read_text(),
        "champion_code": run["champion_code"],
    }
    body = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(data).replace("</", "<\\/"))
    OUT.parent.mkdir(exist_ok=True)
    # docs/index.html: standalone page (GitHub Pages / open locally); docs/report_body.html: same page without
    # the document skeleton, for hosts that add their own.
    html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n' + body + "\n</html>\n")
    OUT.write_text(html)
    (OUT.parent / "report_body.html").write_text(body)
    print(f"wrote {OUT} ({len(html) // 1024} KB) from {run_path.name}, {len(cands)} candidates, memory={memory}")


if __name__ == "__main__":
    main()
