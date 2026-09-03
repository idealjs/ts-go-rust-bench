#!/usr/bin/env python3
"""Minimal dependency-free benchmark runner.

Times a command N times (subprocess wall clock) and reports
min / median / mean / stdev, plus per-run times.

Usage:
  python3 bench/run.py -n 5 -- <command...>
"""
import argparse, statistics, subprocess, sys, time

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5, help="repetitions (default 5)")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("cmd", nargs="+")
    a = ap.parse_args()
    times = []
    for i in range(a.n):
        t0 = time.perf_counter()
        try:
            p = subprocess.run(a.cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=a.timeout)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = -999
        dt = time.perf_counter() - t0
        times.append(dt)
        print(f"run {i+1}: {dt*1000:9.1f} ms (exit {rc})", file=sys.stderr)
    lo = min(times)
    print(f"min={lo*1000:.1f}ms median={statistics.median(times)*1000:.1f}ms "
          f"mean={statistics.mean(times)*1000:.1f}ms "
          f"stdev={statistics.stdev(times)*1000:.1f}ms n={a.n}")

if __name__ == "__main__":
    main()
