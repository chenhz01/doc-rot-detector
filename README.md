# doc-rot-detector

A document reference existence validator. Scans your Markdown docs, extracts every referenced path — links, images, backticked file tokens — and reports which ones no longer exist on disk, with doc, line, and kind. Offline, deterministic, pure standard library, exit code ready for CI.

**Status:** v0.1.1 · Confidence: high (existence checks are exact) · as of 2026-10-11

## Problem

Docs rot in a specific, mechanical way: a file gets renamed, a script moves, and every doc that mentioned it is now lying. Link checkers validate URLs on the internet; nothing cheap validates that the *local* paths your docs cite — in links, images, and inline code — still exist in your repo.

## How it works

1. **Walk**: every `*.md` / `*.markdown` file under the root is read.
2. **Extract**: markdown links `[t](p)`, image embeds `![t](p)`, and backticked tokens that look like paths (`a/b/c.ext`). External URLs, `mailto:`, and `#anchor` links are skipped.
3. **Resolve**: each reference is checked against the doc's own directory and the repo root; a reference that resolves to nothing is reported as broken with file, line number, and kind. Exit `1` if any broken, `2` on bad input.

## Quickstart

```bash
# ~0.8 s total [measured; reproduce: python self_test.py]
python self_test.py

python doc_rot_detector.py path/to/docs          # ~0.2 s per 100 docs [measured]
python doc_rot_detector.py . --json > rot.json   # machine-readable report
```

Example output:

```
doc-rot-detector: root=docs
docs: 3, refs checked: 12, broken: 1, external skipped: 4
BROKEN docs/setup.md:14 [link] old-config.yaml
```

## Why not X

| Alternative | Stars | Why not this |
| --- | --- | --- |
| [ayush698800/docwatcher](https://github.com/ayush698800/docwatcher) | 5 ★ | AI-powered rot detection against git history — a different layer: it judges *semantic* drift. This tool answers the narrower question deterministically: does each referenced path exist on disk right now? |
| [39ff/docker-rotating-proxy](https://github.com/39ff/docker-rotating-proxy) | 181 ★ | Shares the "rotat*" name token only; a proxy server, unrelated to documentation. Listed to disambiguate search noise. |
| [peteletroll/DockRotate](https://github.com/peteletroll/DockRotate) | 14 ★ | Kerbal Space Program robotics mod — name-collision neighbor, not a doc tool at all. |
| Online link checkers | — | Validate http(s) URLs, not local repo paths, and need network. This runs offline in milliseconds. |

## Minimal Fallback

If you cannot run this: `grep -rnoE '\]\([^)]+\)' docs/` to list link targets, then `test -e` each one in a shell loop. Cruder (misses backticked paths and image embeds), but catches the majority of breakage.

## Design Trade-offs

- **Existence, not correctness** — a path can exist and still be the *wrong* file after a refactor; semantic validation is a different (heavier) layer.
- **Backtick heuristic** — tokens like `make all` are skipped (no extension/path shape); this keeps false positives low but may miss extension-free paths like `bin/run`.
- **Two-resolution roots (doc dir + repo root)** — covers most conventions; unusual layouts may need a symlink.
- **No caching** — every run re-walks the tree; simple and always fresh, slower on huge monorepos.

## Limits & Second-order Effects

- Only Markdown is scanned; reStructuredText, asciidoc, and HTML docs are out of scope.
- Path-like *prose* inside backticks (e.g. `v1.2.txt` as a version string) can false-positive if it matches the shape and doesn't exist.
- Second-order: green runs may encourage moving files freely — remember that *content* drift (right file, wrong description) is explicitly not covered.
- Non-UTF-8 docs are reported as broken file entries rather than crashing the whole scan.

## FAQ

**When NOT to use this?**
When you need semantic doc-vs-code drift detection (use an AI-based docwatcher-style layer), when docs live outside the repo they reference, or when you need URL liveness checks for external links — use a network link checker for those.

**Does it modify anything?** No — read-only walk and stat calls.

**Why did my `command --flag` backtick get skipped?** It doesn't look like a path; only extension-shaped or slash-containing tokens are checked.

**CI integration?** Exit 1 on any broken reference — drop it into any CI step.

## Core Assumptions

1. Referenced paths should resolve relative to the doc's directory or the repo root — the two dominant conventions.
2. Existence checking is worth doing deterministically even though it can't judge relevance.
3. Markdown is the documentation format in scope; other formats need a new extractor.
4. The repo being scanned is on local disk; no network checks are performed or wanted.

## LICENSE

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 zhengming contributors.
Contact: hcac4735@agent.qq.com

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [readme-quality-score](https://github.com/chenhz01/readme-quality-score) · [changelog-semantic-lint](https://github.com/chenhz01/changelog-semantic-lint) · [api-contract-drift](https://github.com/chenhz01/api-contract-drift)
