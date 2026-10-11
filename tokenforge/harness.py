"""The referee: compile a candidate matmul kernel into llama2.c, check its greedy output is
byte-identical to the baseline, and measure tokens/sec. Agents never touch this file.
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor"
MODELS = ROOT / "models"
RESULTS = ROOT / "results"
BASELINE_KERNEL = (ROOT / "kernels" / "baseline.c").read_text()

COMPILE_FLAGS = ["-O3"]          # identical for baseline and every candidate
STEPS = 200
RUNS = 5                          # median of 5 timings per item (after 1 untimed warm-up)
SANDBOX = "(version 1)(allow default)(deny network*)"

BLOCKED = re.compile(
    r"\b(system|popen|exec\w*|fork|vfork|fopen|freopen|open|socket|connect|unlink|remove|rename|"
    r"printf|fprintf|puts|fputs|putchar|write|mmap|kill|signal|dlopen|syscall|getenv)\s*\(|"
    r"__asm__|\basm\s*[\(\{]|#\s*include\s*<(?!(arm_neon|dispatch/dispatch|stdint|string|math|stdlib)\.h>)")


@dataclass
class Item:
    model: str
    prompt: str


@dataclass
class Result:
    status: str                      # ok | rejected | compile_error | wrong_output | timeout | crash
    tps: list[float] = field(default_factory=list)
    error_snippet: str = ""
    spread: float = 0.0              # worst (max-min)/median across the repeated timing runs

    @property
    def mean_tps(self) -> float:
        return statistics.mean(self.tps) if self.tps else 0.0


def load_splits() -> dict[str, list[Item]]:
    raw = json.loads((ROOT / "splits.json").read_text())
    return {k: [Item(**i) for i in v] for k, v in raw.items()}


def static_check(code: str) -> str:
    if "matmul" not in code:
        return "no matmul function found"
    m = BLOCKED.search(code)
    return f"blocked construct: {m.group(0)[:60]}" if m else ""


def compile_kernel(code: str, workdir: Path, omp: bool = False) -> tuple[Path | None, str]:
    (workdir / "kernel.c").write_text(code)
    out = workdir / "run"
    cmd = ["clang", *COMPILE_FLAGS, f"-I{workdir}", "-o", str(out), str(VENDOR / "run_tf.c"), "-lm"]
    if omp:  # reference only: upstream's own OpenMP build (make runomp)
        omp_root = "/opt/homebrew/opt/libomp"
        cmd[1:1] = ["-Xpreprocessor", "-fopenmp", f"-I{omp_root}/include"]
        cmd += [f"-L{omp_root}/lib", "-lomp"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "compile timeout"
    if p.returncode != 0:
        errs = [l for l in p.stderr.splitlines() if "error" in l][:3]
        return None, " | ".join(errs)[:400] or p.stderr[:400]
    return out, ""


def run_once(binary: Path, item: Item, timeout: float = 30.0) -> tuple[str, float]:
    cmd = ["sandbox-exec", "-p", SANDBOX, str(binary), str(MODELS / item.model),
           "-z", str(MODELS / "tokenizer.bin"), "-t", "0", "-n", str(STEPS), "-i", item.prompt]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"exit {p.returncode}: {p.stderr[-200:]}")
    m = re.search(r"achieved tok/s:\s*([\d.]+)", p.stderr)
    return p.stdout, float(m.group(1)) if m else 0.0


def reference_outputs() -> dict:
    path = RESULTS / "reference.json"
    return json.loads(path.read_text()) if path.exists() else {}


def key(item: Item) -> str:
    return f"{item.model}::{item.prompt}"


def build_reference(items: list[Item]) -> dict:
    """Greedy outputs of the unmodified baseline kernel; the correctness oracle."""
    RESULTS.mkdir(exist_ok=True)
    ref = reference_outputs()
    with tempfile.TemporaryDirectory() as d:
        binary, err = compile_kernel(BASELINE_KERNEL, Path(d))
        if not binary:
            raise RuntimeError(f"baseline failed to compile: {err}")
        for it in items:
            if key(it) not in ref:
                ref[key(it)] = run_once(binary, it)[0]
    (RESULTS / "reference.json").write_text(json.dumps(ref, indent=1))
    return ref


def evaluate(code: str, items: list[Item], runs: int = RUNS, omp: bool = False) -> Result:
    if not omp:
        reason = static_check(code)
        if reason:
            return Result("rejected", error_snippet=reason)
    ref = reference_outputs()
    with tempfile.TemporaryDirectory() as d:
        binary, err = compile_kernel(code, Path(d), omp=omp)
        if not binary:
            return Result("compile_error", error_snippet=err)
        tps, spreads = [], []
        for it in items:
            samples = []
            for n in range(runs + 1):   # run 0: untimed warm-up (page cache) + correctness check

                try:
                    text, t = run_once(binary, it)
                except subprocess.TimeoutExpired:
                    return Result("timeout", error_snippet=f"> 30s on {it.model}")
                except RuntimeError as e:
                    return Result("crash", error_snippet=str(e)[:300])
                expected = ref.get(key(it))
                if expected is not None and text != expected:
                    i = next((k for k, (a, b) in enumerate(zip(text, expected)) if a != b), min(len(text), len(expected)))
                    return Result("wrong_output",
                                  error_snippet=f"{it.model}: diverged at char {i}: got {text[i:i+40]!r} want {expected[i:i+40]!r}")
                if n > 0:
                    samples.append(t)
            med = statistics.median(samples)
            tps.append(med)
            spreads.append((max(samples) - min(samples)) / med if med else 0.0)
        return Result("ok", tps=tps, spread=max(spreads))


def speedup(cand: Result, base: Result) -> float:
    """Geometric mean of per-item tok/s ratios against a baseline measured in the same round."""
    if cand.status != "ok" or not base.tps:
        return 0.0
    return statistics.geometric_mean([c / b for c, b in zip(cand.tps, base.tps)])


def clang_available() -> bool:
    return shutil.which("clang") is not None and subprocess.run(
        ["clang", "--version"], capture_output=True).returncode == 0
