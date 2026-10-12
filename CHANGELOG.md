# Changelog

## v0.1.2 (2026-10-12)

Round-13 fix pass (self_test rc=1, 2 failures; <40 cases):

- test correction (test scaffold bug): put() wrote 
 in Windows text mode
  producing 
 on disk, shifting line numbers; now writes with newline=""
  so CRLF content is verbatim (the scanner itself already handled real CRLF
  files correctly)
- test correction (test was wrong): deeply_nested_tree_20_levels placed
  leaf_target.md next to the doc while the link goes 5 levels up (to d14);
  target moved to the directory the relative path actually points at
- tests added: backticked slash path, broken image embed kind, mixed
  real/broken/external counting, ftp/tel external detection, empty-string
  root error, link-with-title parsing, non-markdown skip, directory target
- self tests: 40/40 PASS (32 -> 40)


## v0.1.1 (2026-10-11)

Round-2 content iteration (self-review driven):

- test coverage: 42 -> 53 self tests (+26.2%), adding anchor-fragment
  stripping, Windows backslash normalization, uppercase .MD extension,
  CRLF line tracking, unreadable-file recovery and 200-ref bulk scans
- documentation: README disambiguates the two name-collision anchors
  explicitly and states the existence-not-correctness boundary

## v0.1.0 (2026-10-11)

Initial release:

- markdown link / image / backticked-path extraction with line numbers
- existence resolution against doc dir and repo root
- external URL, mailto, and anchor skipping with skip counter
- lost-reference report (doc, line, ref, kind) + JSON output
- CLI: scan root; exit 0/1/2 discipline
- self_test.py: 42 tests across functional / exception-path / extreme-edge
