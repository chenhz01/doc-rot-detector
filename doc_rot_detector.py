#!/usr/bin/env python3
"""doc-rot-detector: document reference existence validator.

Scans Markdown docs and verifies that every referenced local path actually
exists: markdown links, image embeds, and backticked path-like tokens.
Produces a lost-reference list (doc, line, ref). External URLs, anchors,
and mailto links are skipped. Pure standard library, offline, deterministic.
This is a reference-existence checker (layer inverted from doc generators /
AI semantic-drift detectors): it only answers "does the referenced thing
exist on disk?" — it does not judge whether the reference is still correct.
"""
import argparse
import json
import os
import re
import sys

MD_LINK_RE = re.compile(r"(!?)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
PATHISH_RE = re.compile(r"^[\w./\\@ -]+\.[A-Za-z0-9]{1,8}$")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "tel:")


class ScanError(Exception):
    """Raised for unusable inputs."""


def is_external(ref):
    low = ref.lower()
    return low.startswith(EXTERNAL_PREFIXES)


def is_internal_anchor(ref):
    return ref.startswith("#")


def looks_like_path(ref):
    """Heuristic: backticked tokens worth an existence check."""
    if not ref or len(ref) > 200:
        return False
    if any(ch in ref for ch in " \t\n") and "/" not in ref and "\\" not in ref:
        return False
    return bool(PATHISH_RE.match(ref) or ("/" in ref or "\\" in ref))


def extract_refs(text):
    """Yield (line_number, ref, kind) from markdown text."""
    refs = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for match in MD_LINK_RE.finditer(line):
            refs.append((lineno, match.group(2), "link" if match.group(1) == "" else "image"))
        for match in BACKTICK_RE.finditer(line):
            token = match.group(1).strip()
            if looks_like_path(token):
                refs.append((lineno, token, "code-path"))
    return refs


def resolve_ref(ref, doc_path, root):
    """Return True if ref exists relative to the doc's dir or the repo root."""
    ref_norm = ref.replace("\\", "/").split("#")[0].strip()
    if not ref_norm:
        return True  # pure-anchor handled earlier; empty after strip = ok
    candidates = [
        os.path.join(os.path.dirname(doc_path), ref_norm),
        os.path.join(root, ref_norm),
    ]
    return any(os.path.exists(c) for c in candidates)


def scan_docs(root):
    """Walk root recursively for *.md; return (docs_scanned, refs, broken, skipped)."""
    if not os.path.isdir(root):
        raise ScanError("root is not a directory: %s" % root)
    docs_scanned = 0
    refs_checked = 0
    skipped = 0
    broken = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in sorted(filenames):
            if not fname.lower().endswith((".md", ".markdown")):
                continue
            doc_path = os.path.join(dirpath, fname)
            docs_scanned += 1
            try:
                with open(doc_path, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError) as exc:
                broken.append({"doc": doc_path, "line": 0, "ref": "",
                               "kind": "file", "error": "unreadable: %s" % exc})
                continue
            for lineno, ref, kind in extract_refs(text):
                if is_external(ref) or is_internal_anchor(ref):
                    skipped += 1
                    continue
                refs_checked += 1
                if not resolve_ref(ref, doc_path, root):
                    broken.append({"doc": os.path.relpath(doc_path, root),
                                   "line": lineno, "ref": ref, "kind": kind})
    return {"docs_scanned": docs_scanned, "refs_checked": refs_checked,
            "broken": broken, "skipped_external": skipped}


def format_report(report, root):
    lines = ["doc-rot-detector: root=%s" % root,
             "docs: %d, refs checked: %d, broken: %d, external skipped: %d" % (
                 report["docs_scanned"], report["refs_checked"],
                 len(report["broken"]), report["skipped_external"])]
    for item in report["broken"]:
        lines.append("BROKEN %s:%d [%s] %s" % (
            item["doc"], item["line"], item["kind"], item["ref"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="doc-rot-detector", description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="docs root directory")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    args = parser.parse_args(argv)
    try:
        report = scan_docs(args.root)
    except ScanError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report, args.root))
    return 1 if report["broken"] else 0


if __name__ == "__main__":
    sys.exit(main())
