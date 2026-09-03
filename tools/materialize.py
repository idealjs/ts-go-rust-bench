#!/usr/bin/env python3
"""Materialize a TypeScript test-suite case into a self-contained bench dir.

Copies the case (splitting // @filename: sections), rewrites
`/// <reference path="/.lib/..." />` to a local `.lib/` copy, and writes
bench.json with entry files + CLI flags for both compilers.

Usage:
  python3 tools/materialize.py <compiler|conformance> <rel/path/to/case.ts> <out-dir> [entry-basename]
"""
import json, os, re, shutil, sys

SUB = os.environ.get("TS_SUBMODULE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                 "typescript-rust", "_submodules", "TypeScript"))
SUB = os.path.normpath(SUB)

FILE_RE = re.compile(r"^\s*//+\s*@filename:\s*(\S+)\s*$", re.M)
OPT_RE = re.compile(r"^//\s*@(\w+)\s*:\s*(.*)$")

def split_case(text):
    marks = [(m.start(), m.group(1)) for m in FILE_RE.finditer(text)]
    if not marks:
        return [(None, text)]
    files = []
    for i, (pos, name) in enumerate(marks):
        end = marks[i+1][0] if i+1 < len(marks) else len(text)
        body = FILE_RE.sub("", text[pos:end], count=1).lstrip("\n")
        files.append((name, body))
    return files

def build_flags(opts):
    flags = []
    def first(k): return (opts.get(k) or "").split(",")[0].strip().strip('"')
    t = first("target").lower()
    if t: flags += ["--target", t]
    m = first("module")
    if m and m != "none": flags += ["--module", m]
    mr = first("moduleresolution")
    if mr: flags += ["--moduleResolution", mr]
    for k in ("strict", "strictnullchecks", "noimplicitany", "exactoptionalpropertytypes", "allowjs"):
        v = first(k).lower()
        if v in ("true", "false"): flags += [f"--{k}", v]
    j = first("jsx")
    if j: flags += ["--jsx", j]
    jis = first("jsximportsource")
    if jis: flags += ["--jsxImportSource", jis]
    if opts.get("lib"): flags += ["--lib", opts["lib"].replace(" ", ",")]
    if opts.get("types"): flags += ["--types", opts["types"]]
    for k, cli in (("usedefineforclassfields", "useDefineForClassFields"),
                   ("experimentaldecorators", "experimentalDecorators"),
                   ("isolatedmodules", "isolatedModules"),
                   ("importhelpers", "importHelpers")):
        v = first(k)
        if v: flags += [f"--{cli}", v]
    return flags

def main():
    suite, rel, out = sys.argv[1], sys.argv[2], sys.argv[3]
    src = os.path.join(SUB, "tests", "cases", suite, rel)
    text = open(src, encoding="utf-8", errors="replace").read()
    header = text.split("// @filename", 1)[0]
    opts = {m.group(1).lower(): m.group(2).strip()
            for m in OPT_RE.finditer(header) for _ in [1]}
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    entry = []
    for name, body in split_case(text):
        name = (name or os.path.basename(rel)).lstrip("/")
        dst = os.path.join(out, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(body)
        entry.append(name)
    # rewrite /.lib references and copy the fixtures
    libs = set()
    for name, body in split_case(text):
        libs |= set(re.findall(r'reference path="/\.lib/([^"]+)"', body))
    for lib in libs:
        src_lib = os.path.join(SUB, "tests", "lib", lib)
        if os.path.exists(src_lib):
            dst_lib = os.path.join(out, ".lib", lib)
            os.makedirs(os.path.dirname(dst_lib), exist_ok=True)
            shutil.copy(src_lib, dst_lib)
    for name in list(entry) + [""]:
        pass
    for f in glob_real(out):
        s = open(f, encoding="utf-8").read()
        s2 = re.sub(r'(reference path=")/\.lib/([^"]+)"', r"\1.lib/\2", s)
        if s2 != s: open(f, "w", encoding="utf-8").write(s2)
    # The Rust worker parses the RAW case file (it splits @filename
    # sections internally) — keep an unmodified copy under worker/.
    worker_dir = os.path.join(out, "worker")
    os.makedirs(worker_dir, exist_ok=True)
    raw_name = os.path.basename(rel)
    shutil.copy(src, os.path.join(worker_dir, raw_name))
    main_file = [e for e in entry if e == raw_name]
    meta = {
        "suite": suite, "case": rel,
        "flags": build_flags(opts),
        "entry": entry,
        "worker_entry": os.path.join("worker", raw_name),
    }
    json.dump(meta, open(os.path.join(out, "bench.json"), "w"), indent=2)
    print(f"{out}: {len(entry)} files, flags={meta['flags']}")

def glob_real(root):
    for dp, _, ns in os.walk(root):
        for n in ns:
            yield os.path.join(dp, n)

if __name__ == "__main__":
    main()
