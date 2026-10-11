"""Luminal-hosted proposer agents (pattern adapted from DispatchIQ proposers.py).

Agents alternate between MODEL_A (DeepSeek) and MODEL_B (GLM Flash) on Luminal's
OpenAI-compatible API. FALLBACK_BASE_URL/KEY/MODEL is only used if Luminal errors,
and every candidate records which provider/model actually produced it.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from openai import OpenAI

SIGNATURE = "void matmul(float* xout, float* x, float* w, int n, int d)"

STRATEGIES = [
    "Use ARM NEON intrinsics (arm_neon.h) with 4 independent float32x4 accumulators per row.",
    "Unroll the inner loop 4x or 8x and break the floating-point dependency chain.",
    "Parallelize over output rows with Grand Central Dispatch dispatch_apply (dispatch/dispatch.h), chunking rows.",
    "Improve cache behaviour: process several rows at once so each loaded chunk of x is reused.",
    "Combine multithreading over rows (dispatch_apply) with NEON SIMD inside each row.",
    "Study the current champion and remove its biggest remaining bottleneck.",
]

SYSTEM = f"""You are a performance engineer optimizing the hot kernel of a small LLM (llama2.c)
on an Apple M3 Pro (ARM64, 12 cores). Write C code for exactly this function:

    {SIGNATURE}
    // W (d,n) @ x (n,) -> xout (d,). Row i: xout[i] = sum_j w[i*n + j] * x[j]

Rules:
- Output ONE ```c code block containing the full function (plus any static helpers / #includes).
- Allowed headers: arm_neon.h, dispatch/dispatch.h, stdint.h, string.h, math.h, stdlib.h. No I/O, no
  system calls, no inline asm, no other libraries. Compiled with: clang -O3.
- The model's greedy output must stay EXACTLY identical, so keep float32 math numerically close
  to the reference (summation order changes are allowed but risky; keep accuracy high).
- n is a multiple of 4 in all models; handle any tail anyway.
After the code block, write one line: NOTE: <what you tried, under 25 words>"""


@dataclass
class Provider:
    name: str
    base_url: str
    api_key: str


@dataclass
class Proposal:
    code: str
    note: str
    model: str
    provider: str
    strategy: str
    error: str = ""
    tokens: int = 0


def extract_code(text: str) -> str:
    m = re.findall(r"```(?:c|C)?\s*\n(.*?)```", text, re.S)
    return max(m, key=len).strip() if m else ""


def extract_note(text: str) -> str:
    m = re.search(r"NOTE:\s*(.+)", text)
    return m.group(1).strip()[:300] if m else ""


def models() -> list[str]:
    return [m for m in (os.getenv("MODEL_A"), os.getenv("MODEL_B")) if m]


def providers() -> list[Provider]:
    out = []
    if os.getenv("LUMINAL_BASE_URL") and os.getenv("LUMINAL_API_KEY"):
        out.append(Provider("luminal", os.environ["LUMINAL_BASE_URL"], os.environ["LUMINAL_API_KEY"]))
    if os.getenv("FALLBACK_BASE_URL") and os.getenv("FALLBACK_API_KEY"):
        out.append(Provider("fallback", os.environ["FALLBACK_BASE_URL"], os.environ["FALLBACK_API_KEY"]))
    return out


def build_prompt(champion_code: str, champion_tps: float, memories: list[dict], strategy: str) -> str:
    mem_lines = []
    for m in memories:
        if m.get("status") == "ok":
            mem_lines.append(f"- WORKED ({m.get('dev_speedup') or 0:.2f}x vs baseline): {m.get('note','')}")
        else:
            mem_lines.append(f"- FAILED [{m.get('status')}]: {m.get('note','')} :: {(m.get('error_snippet') or '')[:200]}")
    mem = "\n".join(mem_lines) or "- (no history yet)"
    return (f"Current champion ({champion_tps:.1f} tok/s on dev):\n```c\n{champion_code}\n```\n\n"
            f"Relevant past attempts retrieved from team memory:\n{mem}\n\n"
            f"Your angle this round: {strategy}\nWrite an improved full implementation.")


# Luminal currently serves one model (DeepSeek-V4.1-Flash), so the team's diversity comes from
# strategy hints and two thinking modes: "fast" (thinking disabled) and "reasoner" (low effort).
MODES = {"fast": {"thinking": {"type": "disabled"}}, "reasoner": {"reasoning_effort": "low"}}


def propose(agent_idx: int, round_idx: int, champion_code: str, champion_tps: float,
            memories: list[dict], timeout: float = 240.0) -> Proposal:
    ms = models()
    model = ms[agent_idx % len(ms)] if ms else ""
    mode = "fast" if agent_idx % 2 == 0 else "reasoner"
    strategy = STRATEGIES[(agent_idx + round_idx) % len(STRATEGIES)]
    prompt = build_prompt(champion_code, champion_tps, memories, strategy)
    last_err = "no provider configured"
    for p in providers():
        p_model = model if p.name == "luminal" else os.getenv("FALLBACK_MODEL", model)
        try:
            # Streaming avoids the 503s Luminal returns on long non-streamed generations;
            # max_retries backs off on 429/5xx.
            client = OpenAI(base_url=p.base_url, api_key=p.api_key, timeout=timeout, max_retries=4)
            stream = client.chat.completions.create(
                model=p_model, temperature=0.8, max_tokens=8000, stream=True,
                stream_options={"include_usage": True},
                extra_body=MODES[mode] if p.name == "luminal" else None,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
            text, used = "", 0
            for chunk in stream:
                if chunk.usage:
                    used = chunk.usage.total_tokens or 0
                if chunk.choices:
                    text += chunk.choices[0].delta.content or ""
            label = f"{p_model}/{mode}" if p.name == "luminal" else p_model
            err = "" if text else "empty answer (reasoning used the whole token budget)"
            return Proposal(extract_code(text), extract_note(text), label, p.name, strategy, error=err, tokens=used)
        except Exception as e:  # try next provider
            last_err = f"{p.name}: {type(e).__name__}: {e}"[:300]
    return Proposal("", "", model, "none", strategy, error=last_err)
