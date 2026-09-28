# Test fixtures

Synthetic vault exports only. Nothing in this directory may ever come from a real vault.

These files are hand-written to exercise one behaviour each, and `tests/run-tests.py` asserts
against them:

| file | what it exercises |
| --- | --- |
| `mixed-vault.json` | cards, secure notes, trashed items and password-less entries being skipped; the keeper ranking; the passkey/organization cases that must not be decided automatically |
| `parent-domain-only.json` | two different services on one parent domain, sharing a username and password |
| `custom-fields.json` | one copy holding saved fields and an attachment, its twin holding neither |
| `hostile-entries.json` | entry names, usernames and IDs crafted to break out of markup, clobber a control ID, and start a spreadsheet formula |
| `encrypted.json` | a password-protected export, which must be refused |
| `array-root.json` | an export whose root is a list rather than an object |
| `not-json.txt` | a file that is not JSON at all |

Every username, password, domain and ID here is invented. If you add a fixture, keep it that
way: the whole point of this project is that a real export never leaves your machine, and a
fixture committed to a public repository is the one way to break that.
