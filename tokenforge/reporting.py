"""Validated, offline-first evidence shared by Streamlit and the HTML report."""
from __future__ import annotations
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def clean_error(text: str) -> str:
    return re.sub(r"/\S*/(kernel\.c|run_tf\.c):", r"\1:", text or "")

def candidate_path(run_id: str, root: Path = ROOT) -> Path:
    if not re.fullmatch(r"r-[\w-]+", run_id):
        raise ValueError("Invalid run ID")
    return root / "results" / f"{run_id}.candidates.jsonl"

def export_candidates(run_id: str, root: Path = ROOT) -> Path:
    from .memory import Memory
    rows = Memory().all(run_id)
    if not rows:
        raise ValueError(f"No candidates available for {run_id}")
    path = candidate_path(run_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = [{k: v for k, v in row.items() if k != "embedding"} for row in rows]
    for row in safe:
        row["_id"] = str(row["_id"])
        row["error_snippet"] = clean_error(row.get("error_snippet", ""))
    path.write_text("".join(json.dumps(row, default=str) + "\n" for row in safe))
    return path

def load_bundle(run_id: str | None = None, root: Path = ROOT) -> dict:
    paths = sorted((root / "results").glob("r-*.json"))
    if not paths:
        raise ValueError("No recorded runs")
    if run_id:
        candidate_path(run_id, root)
    path = root / "results" / f"{run_id}.json" if run_id else paths[-1]
    run = json.loads(path.read_text())
    run_id = run["run_id"]
    if path.stem != run_id:
        raise ValueError("Run file and run ID disagree")
    source = candidate_path(run_id, root)
    if not source.exists():
        source = root / "results" / "candidates.jsonl"
    rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()] if source.exists() else []
    rows = [row for row in rows if row.get("run_id") == run_id]
    unique = {str(row.get("_id", f"legacy-{i}")): row for i, row in enumerate(rows)}
    rows = sorted(unique.values(), key=lambda row: (row["round"], row["agent"]))
    for rec in run["rounds"]:
        items = [row for row in rows if row["round"] == rec["round"]]
        if len(items) != rec["n_total"] or sum(row["status"] == "ok" for row in items) != rec["n_ok"]:
            raise ValueError(f"Candidate counts disagree in round {rec['round']}; export this run first")
    held_path = root / "results" / "heldout.json"
    held = json.loads(held_path.read_text()) if held_path.exists() else None
    if held and held.get("run_file") != path.name:
        held = None
    if held and held.get("champion_status") == "ok":
        ratios = []
        for item in held["items"]:
            if not all(math.isfinite(item[k]) and item[k] > 0 for k in ("baseline_tps", "champion_tps")):
                raise ValueError("Invalid held-out timings")
            ratios.append(item["champion_tps"] / item["baseline_tps"])
        if not math.isclose(statistics.geometric_mean(ratios), held["speedup_geomean"], rel_tol=1e-6):
            raise ValueError("Held-out aggregate disagrees with item measurements")
    champion_id = None
    rounds = []
    for rec in run["rounds"]:
        champion_id = rec.get("promoted_id") or champion_id
        rounds.append({**rec, "champion_id": champion_id, "n_failed": rec["n_total"] - rec["n_ok"]})
    final = [rec["champion_dev_speedup"] for rec in rounds if rec["champion_id"] == run["champion_id"]]
    cands = []
    for row in rows:
        model = row.get("model", "")
        mode = model.rsplit("/", 1)[-1] if model.endswith(("/fast", "/reasoner")) else "unknown"
        cands.append({**row, "id": str(row.get("_id", "")), "mode": mode, "speedup": row.get("dev_speedup", 0),
                      "val": row.get("val_speedup"), "error": clean_error(row.get("error_snippet", "")),
                      "tokens": row.get("llm_tokens", 0)})
    extra = {}
    for name, relative in {"repair": "learning-study/repair.json", "study": "learning-study/summary.json", "comparison": "comparison.json"}.items():
        artifact = root / "results" / relative
        extra[name] = json.loads(artifact.read_text()) if artifact.exists() else None
    return {"run_id": run_id, "run_file": path.name, "model": run["models"][0] if run["models"] else "",
            "baseline": run["baseline"], "omp_dev": run["reference_omp"]["dev_speedup"], "rounds": rounds,
            "candidates": cands, "heldout": held, "memory": "Atlas export / local replay",
            "champion_id": run["champion_id"], "champion_stats": {"median": statistics.median(final) if final else 1,
            "min": min(final) if final else 1, "max": max(final) if final else 1, "count": len(final)},
            "baseline_code": (root / "kernels" / "baseline.c").read_text(), "champion_code": run["champion_code"],
            "kernel_sha256": hashlib.sha256(run["champion_code"].encode()).hexdigest(), **extra}

def render_report(bundle: dict, root: Path = ROOT, theme: str = "auto") -> str:
    body = (root / "scripts" / "report_template.html").read_text()
    body = body.replace("/*__DATA__*/null", json.dumps(bundle, default=str).replace("</", "<\\/"))
    return '<!doctype html>\n<html lang="en" data-theme="' + theme + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' + body + "</html>\n"
