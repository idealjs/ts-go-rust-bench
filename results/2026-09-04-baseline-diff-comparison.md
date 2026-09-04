# 双端对照：同一上游基线下的 diff 率（2026-09-04）

对比口径：tsc 字节级 errors 基线（`tests/baselines/reference/{compiler,conformance}`，
源自 microsoft/TypeScript JS tsc），语料 12,444 用例。

| | Rust (tsox) | Go (tsgo 7.1.0-dev) |
|---|---|---|
| 全语料 diff / pass / skip | 4,474 / 5,665 / 2,305 | 8,416 / 4,028 / —（单配置口径） |
| **有基线子集（5,917 例）diff 率** | **57.0%**（3,375） | **97.8%**（5,786） |
| 同子集字节级完全一致 | 1,660（28.1%） | **131（2.2%）** |

方法：Go 侧逐用例物化（@filename 拆分、`/.lib` 重写）、解析首配置 flags
（node10→node 平移，否则 Go TS5108 直接拒绝运行）、`tsgo --noEmit` 原生
tsc 格式输出 vs 基线字节比对。抽样验证 diff 为真实差异（如
ArrowFunctionExpression1：Go 报 (2,10) 基线 (1,10)——BOM/行号语义差；
ClassDeclaration10：Go 位置 +2 行且缺 TS7010）。

## 结论

- 上游 JS-tsc 基线**不是 Go 版自己能过的 oracle**——tsgo 对同一基线 97.8% diff，
  其官方仓另行维护自有基线。Rust 移植以同一基线做到 43% 字节一致（error-ful
  子集）+ 0 FAIL（差异全部台账化），严格度显著高于 Go 现状。
- 与 Go 的真实剩余差（同子集内 Go 一致而我们不一致）：**659 例**——这是下一步
  消分诊的实际靶子清单；另有 3,815 例双侧都不一致（多为消息措辞/位置的时代差异）。
