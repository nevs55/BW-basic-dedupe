# Security policy

This tool reads Bitwarden vault exports, which contain credentials in clear text. Security reports are taken seriously.

## Reporting a vulnerability

Use GitHub's [private vulnerability reporting](../../security/advisories/new) (Security tab → Report a vulnerability).

Please don't open a public issue for a security problem until it is fixed.

Expect an acknowledgement within a few days. This is a personal project maintained in spare time, so there is no formal response-time commitment, and there is no bug bounty.

## In scope

Anything that could expose vault data or mislead someone into deleting the wrong credential, including:

- Any path by which the loaded file, or data derived from it, leaves the browser tab — a network request, a link, an embedded resource, anything reachable past the content security policy.
- Passwords or other secrets rendered in the page, written to `localStorage`, `sessionStorage`, IndexedDB, or a cookie, or included in a downloaded file where they are not expected.
- A crafted export that causes script execution in the page (the page builds HTML from entry names, usernames and URIs, and escapes them; a bypass is a vulnerability).
- Grouping or keeper-ranking logic that marks the wrong entry for deletion — for example, failing to detect a passkey or an authenticator code that is present in the export, deciding a group whose copies only share a parent domain, or ignoring saved fields and attachments that one copy holds and its twin does not.

## Out of scope

- The security of Bitwarden itself. Report those to Bitwarden.
- Risks inherent in having an unencrypted export on disk. That is the format's nature; delete the file when you are done.
- Anything that requires an attacker to already have local access to your machine or your unlocked browser profile.
- Copies of this tool hosted on a website. This project is download-only and is not deployed anywhere; a hosted copy asking you to upload a vault export is not mine and should be treated as hostile.

## Verifying a download

Each release lists the SHA-256 of `BW-basic-dedupe.html` in its notes. Check it before use:

```sh
# macOS / Linux
shasum -a 256 BW-basic-dedupe.html

# Windows PowerShell
Get-FileHash BW-basic-dedupe.html -Algorithm SHA256
```

The file in this repository is the same file the releases carry; a hash that does not match either one means you are not holding this tool.

`tests/run-tests.py` repeats the checks that back the claims on the front page — that no request leaves the tab, that the content security policy blocks each outbound channel, that a crafted export cannot execute script, and that the ranking never decides the groups it should leave to you.
