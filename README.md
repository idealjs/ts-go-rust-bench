# ts-go-rust-bench

Benchmark suite comparing the **Go** TypeScript compiler
([typescript-go](https://github.com/microsoft/typescript-go), `tsgo`, TS 7.1.0-dev)
against its in-progress **Rust** port (`tsox`) on identical inputs.

The suite was **designed from data**: we timed both compilers over the full
upstream test corpus — 12,444 cases from `TypeScript/tests/cases/compiler` +
`tests/cases/conformance` — and grouped the cases by what their timings revealed.
Every category below corresponds to a measured behavior, not a guess.

## How the suite was designed

Method of the study (2026-09-04, Linux x64, 6-core):

1. **Go side**: each case materialized to a temp project, compiled with
   `tsgo --noEmit` (flags parsed from the case header). All 12,444 cases.
2. **Rust side**: 442-case stratified sample (150 slowest Rust @6-way
   parallel sweep + 150 slowest Go + 150 random), compiled serially with the
   release-build worker, same worker-process model as the sweep.
3. Paired per-case wall times → ratio distribution.

Key findings that shaped the categories:

| observation | number | consequence |
|---|---|---|
| serial ratio, median | **31×** (rust 1.36s vs go 45ms) | fixed pipeline cost dominates single-file compiles → category `01-startup-floor` |
| Rust floor for any case | ~1.15–1.2s | worker start + default-lib parse/bind/check pipeline is the single biggest Rust gap |
| Go floor | ~40ms (3ms on trivial) | same |
| Rust-hot families (100–300×) | JSX transform, module resolution walks, import helpers/defer, node_modules fixtures | categories `04`–`06`, `09` |
| Both-sides-heavy (go ≥130ms, ratio only 1–9×) | relation/instantiation complexity, huge unions, big control-flow graphs, real-world parser stress | categories `02`, `03`, `07`, `08` — the true algorithmic core |

## Categories

| dir | what it measures | evidence (rust/go, serial) |
|---|---|---|
| `01-startup-floor` | process start + default-lib pipeline on trivial files | 6.7s vs 44ms (numericUnderscoredSeparator) |
| `02-relation-stress` | structural relation/instantiation complexity | 1.15s vs 1.44s (relationComplexityError) — go's own worst case |
| `03-type-inference` | conditional/mapped/template-literal inference, huge tuples | 1.2s vs 462ms (templateLiteralTypes1) |
| `04-jsx` | TSX check + jsx-runtime transform pipeline | 12.6s vs 40ms (commentsOnJSXExpressionsArePreserved) |
| `05-module-resolution` | node_modules / bundler / exports walks | 10.5s vs 44ms (moduleResolutionWithModule) |
| `06-import-defer` | `import defer` + importHelpers/tslib handling | 6.7s vs 43ms family-wide |
| `07-control-flow` | large CFG narrowing, static blocks | 1.37s vs 230ms (largeControlFlowGraph) |
| `08-parser-realworld` | parsing real multi-KLOC TS sources | 1.22s vs 173ms (parserindenter) |
| `09-isolated-modules` | isolatedModules/declarations checks, triple-slash types | 4.9s vs 44ms |

## Usage

```sh
# one category entry, both compilers, 5 reps:
TSGO=/path/to/tsgo TSOX=/path/to/tsox-worker \
  python3 bench/compare.py --n 5 --filter 04-jsx --markdown

# time a single command:
python3 bench/run.py -n 5 -- tsgo --noEmit cases/02-relation-stress/relationComplexityError/relationComplexityError.ts
```

`TSOX` is the `submodule_compiler` **worker test binary** of the Rust port
(`target/{release}/deps/submodule_compiler-*`), invoked in the same
one-process-per-case mode the port's own regression harness uses.
`bench.json` in each case dir pins the CLI flags (parsed from the upstream
case header) and the entry files.

## Methodology notes

- `--noEmit`: checker-focused; emit cost is out of scope for now.
- Compiler flags come from each upstream case header (`bench.json`); no
  global `--skipLibCheck` is applied on either side.
- Cases replaced for scope: `deeplyDependentLargeArrayMutation2` required
  `allowJs` (unsupported by the Rust harness) — replaced by
  `nestedLoopTypeGuards` in `07-control-flow`.
- Timing benches do not require output parity; each case is a workload
  representative of its upstream family. Output correctness is governed by
  the 12,466-case regression sweep, not here.
- Timing **includes process start and lib load** — deliberately: the
  "compile one project" end-to-end latency is the user-visible quantity.
  `01-startup-floor` exists exactly to make that fixed cost visible.
- Statistic: **min of n** (CPU-bound work; median also reported by `run.py`).
- Cases are drawn from Microsoft/TypeScript's test suite (Apache-2.0) and
  made self-contained (multi-file sections split, `/.lib` fixtures copied
  locally). Each case keeps its upstream path in `bench.json`.
- Rust port state pinned per results file (commit hash in `results/`).

## Results

- [`results/2026-09-04.md`](results/2026-09-04.md) — first full run.

## License

Runners and tooling: MIT. Test cases: Apache-2.0 (Microsoft/TypeScript).
