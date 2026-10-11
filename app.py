"""TokenForge dashboard: streamlit run app.py"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
from tokenforge.memory import Memory  # noqa: E402

ROOT = Path(__file__).parent
st.set_page_config(page_title="TokenForge", layout="wide")
st.title("TokenForge — agents that make an on-device LLM faster")
st.caption("6 agents on Luminal (DeepSeek-V4.1-Flash, 'fast' and 'reasoner' modes) rewrite llama2.c's matmul. A fixed harness requires "
           "byte-identical greedy output and measures tok/s on an Apple M3 Pro. MongoDB stores every attempt "
           "and feeds relevant wins and failures into the next round.")

runs = sorted((ROOT / "results").glob("r-*.json"))
if not runs:
    st.info("No run yet. Start one with: python evolve.py --rounds 8 --agents 6")
    st.stop()
run_file = st.sidebar.selectbox("Run", [r.name for r in reversed(runs)])
run = json.loads((ROOT / "results" / run_file).read_text())
rounds = pd.DataFrame(run["rounds"])
held_path = ROOT / "results" / "heldout.json"
held = json.loads(held_path.read_text()) if held_path.exists() else None
if st.sidebar.button("Refresh"):
    st.rerun()

# --- Scorecard mapped to the judging criteria (no blended number) ---
base_tps = sum(run["baseline"]["dev_tps"]) / max(len(run["baseline"]["dev_tps"]), 1)
sp = rounds["champion_dev_speedup"] if len(rounds) else pd.Series([1.0])
champ_sp = float(sp.median())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Baseline (dev)", f"{base_tps:.0f} tok/s", help="stock llama2.c matmul, clang -O3")
c2.metric("Champion (dev, median)", f"{champ_sp:.2f}x",
          help=f"re-measured every round; range {sp.min():.2f}x-{sp.max():.2f}x (laptop timing noise)")
c3.metric("Held-out (fresh tests)", f"{held['speedup_geomean']:.2f}x" if held else "not run yet",
          help="stories110M + new prompts, never used while optimizing; run once")
c4.metric("Upstream OpenMP build (reference)", f"{run['reference_omp']['dev_speedup']:.2f}x",
          help="llama2.c's own `make runomp`, for context")

st.subheader("Improvement over rounds")
if len(rounds):
    st.line_chart(rounds.set_index("round")[["champion_dev_speedup", "best_dev_speedup"]])

mem = Memory()
docs = mem.all(run["run_id"])
source = mem.backend
if not docs:  # runs made before Atlas was connected live in the local JSONL log
    jl = ROOT / "results" / "candidates.jsonl"
    docs = [d for d in (json.loads(l) for l in jl.read_text().splitlines()) if d.get("run_id") == run["run_id"]] \
        if jl.exists() else []
    source = "local jsonl"
st.sidebar.caption(f"Memory source for this run: {source}")
df = pd.DataFrame(docs)
if len(df):  # readable labels: "fast" / "reasoner" instead of the full model id; no temp paths
    df["model"] = df["model"].fillna("").str.split("/").str[-1].replace({"": "unknown"})
    df["error_snippet"] = df["error_snippet"].fillna("").str.replace(r"/\S*/(kernel\.c|run_tf\.c):", r"\1:", regex=True)
    for c in ("dev_speedup", "val_speedup"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(2)
if len(df):
    left, right = st.columns(2)
    with left:
        st.subheader("Every candidate")
        st.scatter_chart(df, x="round", y="dev_speedup", color="status")
    with right:
        st.subheader("Team learning: correct candidates per round")
        st.bar_chart(rounds.set_index("round")[["n_ok", "n_total"]])

    st.subheader("Which model wins?")
    if "llm_tokens" not in df:
        df["llm_tokens"] = 0
    by = df.groupby("model").agg(attempts=("status", "size"),
                                 correct=("status", lambda s: (s == "ok").sum()),
                                 promoted=("promoted", "sum"),
                                 best_speedup=("dev_speedup", "max"),
                                 llm_tokens=("llm_tokens", "sum")).reset_index()
    st.dataframe(by, hide_index=True)
    total_tokens = int(df["llm_tokens"].fillna(0).sum())
    gain = (champ_sp - 1) * 100
    st.caption(f"Luminal tokens used: {total_tokens:,}" +
               (f" — {total_tokens / gain:,.0f} tokens per 1% speedup" if gain > 0 else ""))

    st.subheader("Lineage of champions")
    lin = df[df["promoted"] == True][["round", "model", "dev_speedup", "val_speedup", "note"]]  # noqa: E712
    if len(lin):
        st.dataframe(lin, hide_index=True)
    else:
        st.write("No promotion yet.")

    st.subheader("Failures the team learned from")
    st.dataframe(df[df["status"] != "ok"][["round", "model", "status", "error_snippet"]].tail(10), hide_index=True)

if held:
    st.subheader("Held-out results (run once)")
    st.dataframe(pd.DataFrame(held["items"]), hide_index=True)
    if held.get("forced"):
        st.warning("The held-out test was re-run with --force.")

st.subheader("Kernel: baseline vs champion")
a, b = st.columns(2)
a.code((ROOT / "kernels" / "baseline.c").read_text(), language="c")
b.code(run["champion_code"], language="c")
