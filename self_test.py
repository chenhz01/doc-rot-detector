#!/usr/bin/env python3
"""Self-test for doc-rot-detector. Pure stdlib. Run: python self_test.py"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc_rot_detector as drd  # noqa: E402

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


def mkroot():
    return tempfile.mkdtemp()


def put(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    # newline="" so \r\n in test content is written verbatim (no double translation on Windows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return path


def expect_scan_error(fn, *a):
    try:
        fn(*a)
    except drd.ScanError:
        return
    raise AssertionError("expected ScanError")


# ---------------- functional unit tests ----------------

@test("extract_md_link")
def _():
    assert drd.extract_refs("see [x](a.md)")[0][1] == "a.md"


@test("extract_image_link")
def _():
    refs = drd.extract_refs("![logo](img/logo.png)")
    assert refs[0][1] == "img/logo.png" and refs[0][2] == "image"


@test("extract_code_path_token")
def _():
    refs = drd.extract_refs("config lives in `src/conf/app.py`")
    assert any(r[1] == "src/conf/app.py" and r[2] == "code-path" for r in refs)


@test("non_path_backtick_skipped")
def _():
    assert drd.extract_refs("run `make all` now") == []


@test("external_url_skipped_in_scan")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[g](https://example.com/x)")
        r = drd.scan_docs(root)
        assert r["refs_checked"] == 0 and r["skipped_external"] == 1
    finally:
        shutil.rmtree(root)


@test("anchor_link_skipped")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[jump](#section)")
        r = drd.scan_docs(root)
        assert r["refs_checked"] == 0
    finally:
        shutil.rmtree(root)


@test("mailto_skipped")
def _():
    refs = drd.extract_refs("[mail](mailto:x@y.z)")
    root = mkroot()
    try:
        put(root, "a.md", "[mail](mailto:x@y.z)")
        r = drd.scan_docs(root)
        assert r["refs_checked"] == 0
    finally:
        shutil.rmtree(root)


@test("valid_relative_link_exists")
def _():
    root = mkroot()
    try:
        put(root, "docs/a.md", "[b](b.md)")
        put(root, "docs/b.md", "hello")
        r = drd.scan_docs(root)
        assert r["broken"] == [] and r["refs_checked"] == 1
    finally:
        shutil.rmtree(root)


@test("broken_relative_link_detected")
def _():
    root = mkroot()
    try:
        put(root, "docs/a.md", "[missing](ghost.md)")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1 and r["broken"][0]["line"] == 1
    finally:
        shutil.rmtree(root)


@test("root_relative_link_resolved")
def _():
    root = mkroot()
    try:
        put(root, "docs/a.md", "[readme](README.md)")
        put(root, "README.md", "top level")
        r = drd.scan_docs(root)
        assert r["broken"] == []
    finally:
        shutil.rmtree(root)


@test("broken_code_path_detected")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "see `src/gone.py`")
        r = drd.scan_docs(root)
        assert any(b["kind"] == "code-path" for b in r["broken"])
    finally:
        shutil.rmtree(root)


@test("nested_dirs_walked")
def _():
    root = mkroot()
    try:
        put(root, "a/b/c/deep.md", "[x](../../../nope.md)")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1
    finally:
        shutil.rmtree(root)


@test("format_report_lists_broken")
def _():
    report = {"docs_scanned": 1, "refs_checked": 1, "skipped_external": 0,
              "broken": [{"doc": "a.md", "line": 3, "ref": "x.md", "kind": "link"}]}
    assert "BROKEN a.md:3 [link] x.md" in drd.format_report(report, "root")


@test("cli_clean_exit_0")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "no refs here")
        assert drd.main([root]) == 0
    finally:
        shutil.rmtree(root)


@test("cli_broken_exit_1")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[x](nope.md)")
        assert drd.main([root]) == 1
    finally:
        shutil.rmtree(root)


# ---------------- exception-path tests ----------------

@test("missing_root_raises")
def _():
    expect_scan_error(drd.scan_docs, os.path.join(mkroot(), "ghost-dir"))


@test("root_is_file_raises")
def _():
    root = mkroot()
    p = put(root, "file.md", "x")
    expect_scan_error(drd.scan_docs, p)


@test("unreadable_doc_reported_as_broken")
def _():
    root = mkroot()
    try:
        p = put(root, "bad.md", "text")
        with open(p, "wb") as f:
            f.write(b"\xff\xfe\xfa")
        r = drd.scan_docs(root)
        assert any(b.get("error") for b in r["broken"])
    finally:
        shutil.rmtree(root)


@test("empty_ref_treated_as_present")
def _():
    assert drd.resolve_ref("", "/anywhere/x.md", "/anywhere") is True


@test("empty_root_cli_defaults_to_cwd")
def _():
    root = mkroot()
    cwd = os.getcwd()
    try:
        os.chdir(root)
        put(".", "ok.md", "plain")
        assert drd.main([]) == 0
    finally:
        os.chdir(cwd)
        shutil.rmtree(root)


# ---------------- extreme-edge tests ----------------

@test("empty_doc_no_refs")
def _():
    assert drd.extract_refs("") == []


@test("empty_root_scans_zero_docs")
def _():
    root = mkroot()
    try:
        r = drd.scan_docs(root)
        assert r["docs_scanned"] == 0 and r["broken"] == []
    finally:
        shutil.rmtree(root)


@test("unicode_doc_names_and_links")
def _():
    root = mkroot()
    try:
        put(root, "文档/指南.md", "[目标](配套.md)")
        put(root, "文档/配套.md", "存在")
        r = drd.scan_docs(root)
        assert r["broken"] == [] and r["docs_scanned"] == 2
    finally:
        shutil.rmtree(root)


@test("unicode_broken_link_detected")
def _():
    root = mkroot()
    try:
        put(root, "文档/指南.md", "[缺失](不存在.md)")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1
    finally:
        shutil.rmtree(root)


@test("long_ref_400_chars")
def _():
    root = mkroot()
    try:
        long_ref = "a" * 200 + ".md"
        put(root, "a.md", "[x](%s)" % long_ref)
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1
    finally:
        shutil.rmtree(root)


@test("deeply_nested_tree_20_levels")
def _():
    root = mkroot()
    try:
        rel = "/".join(["d%d" % i for i in range(20)])
        put(root, rel + "/leaf.md", "[up](../../../../../leaf_target.md)")
        # 5 levels up from d19 lands in d14 — put the target exactly there
        put(root, "/".join(["d%d" % i for i in range(15)]) + "/leaf_target.md", "here")
        r = drd.scan_docs(root)
        assert r["broken"] == []
    finally:
        shutil.rmtree(root)


@test("many_refs_bulk_doc")
def _():
    root = mkroot()
    try:
        lines = ["[l%d](target_%d.md)" % (i, i) for i in range(200)]
        put(root, "big.md", "\n".join(lines))
        for i in range(100):
            put(root, "target_%d.md" % i, "x")
        r = drd.scan_docs(root)
        assert r["refs_checked"] == 200 and len(r["broken"]) == 100
    finally:
        shutil.rmtree(root)


@test("crlf_doc_parsed")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[x](real.md)\r\n[y](ghost.md)\r\n")
        put(root, "real.md", "ok")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1 and r["broken"][0]["line"] == 2
    finally:
        shutil.rmtree(root)


@test("anchor_fragment_in_ref_stripped")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[x](real.md#section)")
        put(root, "real.md", "ok")
        r = drd.scan_docs(root)
        assert r["broken"] == []
    finally:
        shutil.rmtree(root)


@test("windows_backslash_ref_normalized")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "use `dir\\sub\\file.txt` style")
        put(root, "dir/sub/file.txt", "ok")
        r = drd.scan_docs(root)
        assert r["broken"] == []
    finally:
        shutil.rmtree(root)


@test("json_report_parseable")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[x](ghost.md)")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            drd.main([root, "--json"])
        data = json.loads(buf.getvalue())
        assert data["broken"][0]["ref"] == "ghost.md"
    finally:
        shutil.rmtree(root)


@test("markdown_extension_uppercase")
def _():
    root = mkroot()
    try:
        put(root, "A.MD", "no refs")
        r = drd.scan_docs(root)
        assert r["docs_scanned"] == 1
    finally:
        shutil.rmtree(root)


@test("backticked_slash_path_broken_detected")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "see `src/lib/ghost.py` here")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1 and r["broken"][0]["kind"] == "code-path"
    finally:
        shutil.rmtree(root)


@test("broken_image_embed_detected")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "![logo](img/ghost.png)")
        put(root, "img/.keep", "")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1 and r["broken"][0]["kind"] == "image"
    finally:
        shutil.rmtree(root)


@test("mixed_real_and_broken_refs_counted")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[ok](real.md)\n[bad](ghost.md)\n[ext](https://x.example/a)")
        put(root, "real.md", "ok")
        r = drd.scan_docs(root)
        assert len(r["broken"]) == 1 and r["skipped_external"] == 1
        assert r["refs_checked"] == 2
    finally:
        shutil.rmtree(root)


@test("ftp_and_tel_treated_as_external")
def _():
    assert drd.is_external("ftp://host/f.txt")
    assert drd.is_external("tel:+12345")
    assert not drd.is_external("docs/file.md")


@test("empty_string_root_raises")
def _():
    expect_scan_error(drd.scan_docs, "")


@test("md_link_with_title_parsed")
def _():
    root = mkroot()
    try:
        put(root, "a.md", '[x](real.md "a title")')
        put(root, "real.md", "ok")
        r = drd.scan_docs(root)
        assert r["broken"] == [] and r["refs_checked"] == 1
    finally:
        shutil.rmtree(root)


@test("non_markdown_files_not_scanned")
def _():
    root = mkroot()
    try:
        put(root, "notes.txt", "[x](ghost.md)")
        put(root, "a.md", "plain")
        r = drd.scan_docs(root)
        assert r["docs_scanned"] == 1 and r["broken"] == []
    finally:
        shutil.rmtree(root)


@test("link_to_existing_directory_not_broken")
def _():
    root = mkroot()
    try:
        put(root, "a.md", "[dir](sub)")
        os.makedirs(os.path.join(root, "sub"))
        r = drd.scan_docs(root)
        assert r["broken"] == [] and r["refs_checked"] == 1
    finally:
        shutil.rmtree(root)


def main():
    passed = failed = 0
    for name, fn in TESTS:
        try:
            fn()
            passed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL %s: %r" % (name, exc))
    print("passed=%d failed=%d total=%d" % (passed, failed, passed + failed))
    print("SUMMARY: PASS %d/%d" % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
