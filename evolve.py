"""Self-improving agent team: propose (Luminal, in parallel) -> test (harness, sequential) -> learn (MongoDB).

    python evolve.py --rounds 8 --agents 6
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from tokenforge import agents, harness  # noqa: E402
from tokenforge.memory import Memory  # noqa: E402

ROOT = Path(__file__).parent
PROMOTE_MARGIN = 1.05   # must beat champion on dev by 5% (measured timing spread is ~5-8%)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--agents", type=int, default=6)
    ap.add_argument("--runs", type=int, default=harness.RUNS)
    a = ap.parse_args()

    if not harness.clang_available():
        sys.exit("clang is not usable. Run: sudo xcodebuild -license accept")
    if not agents.providers() or not agents.models():
        sys.exit("Set LUMINAL_BASE_URL, LUMINAL_API_KEY, MODEL_A, MODEL_B in .env")

    splits = harness.load_splits()
    dev, val = splits["dev"], splits["validation"]
    harness.build_reference(dev + val)
    mem = Memory()
    run_id = datetime.now().strftime("r-%Y%m%d-%H%M%S")
    out = ROOT / "results" / f"{run_id}.json"
    print(f"[{run_id}] memory={mem.backend} models={agents.models()} providers={[p.name for p in agents.providers()]}")

    base = harness.BASELINE_KERNEL
    b_dev, b_val = harness.evaluate(base, dev, a.runs), harness.evaluate(base, val, a.runs)
    omp = harness.evaluate(base, dev, a.runs, omp=True)   # reference line: upstream `make runomp`
    state = {"run_id": run_id, "started": now(), "models": agents.models(),
             "baseline": {"dev_tps": b_dev.tps, "val_tps": b_val.tps},
             "reference_omp": {"status": omp.status, "dev_speedup": harness.speedup(omp, b_dev)},
             "rounds": [], "champion_id": None, "champion_code": base}
    print(f"round 0  baseline dev {b_dev.mean_tps:.1f} tok/s | val {b_val.mean_tps:.1f} tok/s | "
          f"upstream OpenMP reference {state['reference_omp']['dev_speedup']:.2f}x")

    champ_code, champ_id, champ_tps = base, None, b_dev.mean_tps
    for r in range(1, a.rounds + 1):
        mems = [mem.retrieve(agents.STRATEGIES[(i + r) % len(agents.STRATEGIES)], run_id) for i in range(a.agents)]
        with ThreadPoolExecutor(a.agents) as ex:
            props = list(ex.map(lambda i: agents.propose(i, r, champ_code, champ_tps, mems[i]), range(a.agents)))

        # Timing runs are sequential so candidates never compete for cores.
        b_dev = harness.evaluate(base, dev, a.runs)
        c_dev = harness.evaluate(champ_code, dev, a.runs)
        champ_sp = harness.speedup(c_dev, b_dev)
        scored = []
        for i, p in enumerate(props):
            res = harness.Result("no_code", error_snippet=p.error or "model returned no code block") \
                if not p.code else harness.evaluate(p.code, dev, a.runs)
            sp = harness.speedup(res, b_dev)
            doc = {"run_id": run_id, "round": r, "agent": i, "model": p.model, "provider": p.provider,
                   "strategy": p.strategy, "note": p.note, "code": p.code, "parent_id": champ_id,
                   "status": res.status, "error_snippet": res.error_snippet, "dev_tps": res.tps,
                   "dev_speedup": sp, "val_speedup": None, "promoted": False, "llm_tokens": p.tokens}
            scored.append((sp, doc))
            print(f"  r{r} a{i} {p.model:<28} {res.status:<13} {sp:5.2f}x  {p.note[:60]}")

        promoted = None
        ok = sorted([s for s in scored if s[1]["status"] == "ok"], key=lambda s: -s[0])
        if ok and ok[0][0] > champ_sp * PROMOTE_MARGIN:
            best = ok[0][1]
            b_val = harness.evaluate(base, val, a.runs)
            v_cand = harness.speedup(harness.evaluate(best["code"], val, a.runs), b_val)
            v_champ = harness.speedup(harness.evaluate(champ_code, val, a.runs), b_val)
            best["val_speedup"] = v_cand
            if v_cand > v_champ:
                best["promoted"] = True
                promoted = best
        for _, doc in scored:
            doc_id = mem.add(doc)
            if doc is promoted:
                champ_code, champ_id = doc["code"], doc_id
                champ_tps = doc["dev_speedup"] * b_dev.mean_tps
                champ_sp = doc["dev_speedup"]

        rec = {"run_id": run_id, "round": r, "base_dev_tps": b_dev.mean_tps, "champion_dev_speedup": champ_sp,
               "champion_val_speedup": promoted["val_speedup"] if promoted else
               (state["rounds"][-1]["champion_val_speedup"] if state["rounds"] else 1.0),
               "best_dev_speedup": ok[0][0] if ok else 0.0, "n_ok": len(ok), "n_total": len(scored),
               "llm_tokens": sum(p.tokens for p in props), "champion_timing_spread": c_dev.spread,
               "promoted_id": champ_id if promoted else None,
               "promoted_model": promoted["model"] if promoted else None, "ts": now()}
        state["rounds"].append(rec)
        state.update(champion_id=champ_id, champion_code=champ_code)
        mem.log_round(dict(rec))
        out.write_text(json.dumps(state, indent=1))
        (ROOT / "kernels" / "champion.c").write_text(champ_code)
        print(f"round {r}: champion {champ_sp:.2f}x dev | {len(ok)}/{len(scored)} correct | "
              f"{'PROMOTED ' + promoted['model'] if promoted else 'no promotion'}")

    print(f"done -> {out}  champion kernel -> kernels/champion.c")


if __name__ == "__main__":
    main()
