import pytest

from tokenforge import harness
from tokenforge.agents import extract_code, extract_note

needs_clang = pytest.mark.skipif(not harness.clang_available(), reason="clang unavailable (Xcode license?)")
DEV = [harness.Item("stories15M.bin", "Once upon a time")]

WRONG = """void matmul(float* xout, float* x, float* w, int n, int d) {
    for (int i = 0; i < d; i++) { float v = 0; for (int j = 0; j < n; j++) v += w[i*n+j] * x[j]; xout[i] = v * 1.01f; }
}"""
LOOP = """void matmul(float* xout, float* x, float* w, int n, int d) { volatile int k = 1; while (k) {} }"""


def test_static_check_blocks_system_calls():
    assert harness.static_check('void matmul(){ system("rm -rf /"); }').startswith("blocked")
    assert harness.static_check("#include <stdio.h>\nvoid matmul(){}").startswith("blocked")
    assert harness.static_check(harness.BASELINE_KERNEL) == ""
    # regression: a comment mentioning "execution (" was wrongly rejected in run r-20261011-170439
    assert harness.static_check("void matmul(){ /* fast execution (NEON) */ }") == ""
    assert harness.static_check("void matmul(){ execve(0, 0, 0); }").startswith("blocked")
    assert harness.static_check("#include <arm_neon.h>\n#include <dispatch/dispatch.h>\nvoid matmul(){}") == ""


def test_extract_code_and_note():
    text = "here\n```c\nvoid matmul(){}\n```\nNOTE: tried NEON"
    assert extract_code(text) == "void matmul(){}"
    assert extract_note(text) == "tried NEON"


def test_rejected_without_compiling():
    assert harness.evaluate('void matmul(){ fork(); }', DEV, runs=1).status == "rejected"


@needs_clang
def test_baseline_is_correct():
    harness.build_reference(DEV)
    r = harness.evaluate(harness.BASELINE_KERNEL, DEV, runs=1)
    assert r.status == "ok" and r.tps[0] > 0


@needs_clang
def test_wrong_kernel_is_caught():
    harness.build_reference(DEV)
    assert harness.evaluate(WRONG, DEV, runs=1).status == "wrong_output"


@needs_clang
def test_compile_error_reported():
    harness.build_reference(DEV)
    r = harness.evaluate("void matmul(float* xout) { this is not C }", DEV, runs=1)
    assert r.status == "compile_error" and r.error_snippet


@needs_clang
def test_infinite_loop_times_out(monkeypatch):
    harness.build_reference(DEV)
    real = harness.run_once
    monkeypatch.setattr(harness, "run_once", lambda b, it, timeout=30.0: real(b, it, timeout=3.0))
    assert harness.evaluate(LOOP, DEV, runs=1).status == "timeout"
