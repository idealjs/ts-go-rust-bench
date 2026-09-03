#!/usr/bin/env python3
"""Compare tsgo (Go) vs tsox (Rust) over cases/.

Each case directory contains the source files plus `bench.json`:
  { "flags": ["--target", "es2015", ...], "entry": ["main.ts", ...] }

Environment:
  TSGO   path to the Go tsc binary (default: tsgo on PATH)
  TSOX   path to the Rust worker test binary (default: ../../typescript-rust/
         target/release/deps/submodule_compiler-*), invoked in worker mode

Usage: python3 bench/compare.py [--n 3] [--filter substr] [--markdown]
"""
import argparse, glob, json, os, statistics, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(ROOT, "cases")

def find_tsox():
    env = os.environ.get("TSOX")
    if env:
        return env
    hits = sorted(glob.glob(os.path.join(ROOT, "..", "typescript-rust",
                 "target", "release", "deps", "submodule_compiler-*")))
    hits = [h for h in hits if not h.endswith(".d")]
    return hits[0] if hits else None

def timeit(cmd, n, timeout=300):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        times.append(time.perf_counter() - t0)
        if p.returncode not in (0, 2):
            break
    return times

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--filter", default="")
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args()
    tsgo = os.environ.get("TSGO", "tsgo")
    tsox = find_tsox()
    dirs = sorted(d for d in glob.glob(os.path.join(CASES, "*", "*")) if os.path.isdir(d))
    rows = []
    for d in dirs:
        cat = os.path.basename(os.path.dirname(d))
        name = os.path.basename(d)
        full = f"{cat}/{name}"
        if a.filter and a.filter not in full:
            continue
        meta = json.load(open(os.path.join(d, "bench.json")))
        entry = [os.path.join(d, e) for e in meta["entry"]]
        go_cmd = [tsgo, "--noEmit"] + meta["flags"] + entry
        rs_cmd = [tsox, "--exact", "submodule_compiler_cases", "--nocapture"]
        env = dict(os.environ, TSOX_SUBMODULE_WORKER=os.path.join(d, meta["worker_entry"]),
                   TSOX_SUBMODULE_OUT=os.path.join(d, ".out.json"))
        gt = timeit(go_cmd, a.n)
        t0 = time.perf_counter()
        subprocess.run(rs_cmd, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=300)
        rt = [time.perf_counter() - t0]
        rows.append((full, min(gt) * 1000, statistics.median(gt) * 1000, rt[0] * 1000))
        speedup = rt[0] / min(gt) if min(gt) > 0 else 0
        print(f"{full:55s} go={min(gt)*1000:9.1f}ms  rust={rt[0]*1000:9.1f}ms  x{speedup:8.1f}")
    if a.markdown:
        print("\n| case | tsgo min | tsox | ratio |")
        print("|---|---|---|---|")
        for full, gmin, gmed, r in rows:
            print(f"| {full} | {gmin:.1f}ms | {r:.1f}ms | {r/gmin:.1f}x |")

if __name__ == "__main__":
    main()
