# Changelog

## Unreleased — security fixes on top of upstream `v0.1` (`12f6e13`)

Found in a read-only review of the upstream revision, then fixed here. Each fix has a
fixture behind it in `tests/fixtures/`, and all of them are asserted by
`tests/run-tests.py`.

### Fixed

- **Groups matched only on a parent domain are no longer decided for you.** `mail.example.com`
  and `vpn.example.com` with the same username and a reused password were merged and one was
  silently preselected for deletion. They may be two different accounts. Such a group now
  carries a warning and preselects nothing. Groups whose copies do share a saved website
  (`amazon.com`, `www.amazon.com`, `smile.amazon.com`) behave as before.
- **The keeper ranking now counts what a copy holds that its twin cannot replace.** Saved
  fields (security answers, recovery codes), attachments and password history were ignored, so
  a copy holding them could be marked for deletion in favour of an emptier copy. They now rank
  above presentation metadata, and copies whose saved fields differ are left for you to decide.
  Recency, previously a score of its own, is now only the tie-break it was documented to be.
- **The delete list can no longer carry a spreadsheet formula.** An entry name or username
  starting with `=`, `+`, `-` or `@` is run as a formula when the CSV is opened in Excel or
  Sheets; such a cell is now prefixed with an apostrophe so it stays literal text.
- **`esc()` also escapes the apostrophe.** Every attribute the page generates is double quoted,
  so this was not exploitable, but it removes the trap for the next edit.
- **Dead code in the security-critical ranker:** a ternary whose branches were identical, a
  write-only `anySecurity` field, and a recency term that could only ever add 0 or 1.

### Changed

- **Documentation tells the truth about the artefact.** README and SECURITY.md named a
  `vault-duplicate-review.html` that exists in neither the repository nor the releases, and
  SECURITY.md promised a SHA-256 that no release listed. The filename is now the real
  `BW-basic-dedupe.html` and the hash lives in the release notes.
- The README's passkey caveat now cites Bitwarden's own statement that passkeys are included in
  JSON exports, while keeping the warning that an older client may omit the field.

### Added

- **`tests/run-tests.py`** — a browser suite covering grouping, ranking, the never-decided
  cases, escaping of a crafted export, CSV output, input validation, and the no-network claim.
- **`.github/workflows/tests.yml`** — runs that suite on every push and pull request.

## v0.1 — upstream

First release of the upstream project: [Noneyabizzy/BW-basic-dedupe](https://github.com/Noneyabizzy/BW-basic-dedupe).
