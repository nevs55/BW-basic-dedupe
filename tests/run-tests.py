#!/usr/bin/env python3
"""End-to-end checks for BW-basic-dedupe.

Every claim the tool makes is verified by running it in a real browser against a synthetic
export, not by reading the source. Run it after any change to the HTML file:

    pip install playwright
    playwright install chromium
    python3 tests/run-tests.py

Set CHROME_PATH to use an already-installed Chrome instead of the downloaded one:

    CHROME_PATH=/usr/bin/google-chrome python3 tests/run-tests.py
"""

import json
import os
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTEFACT = ROOT / "BW-basic-dedupe.html"
FIXTURES = ROOT / "tests" / "fixtures"
URL = ARTEFACT.as_uri()

checks = []


def check(name, ok, detail=None):
    checks.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, ("  <- " + str(detail)) if (detail and not ok) else ""))


STATE_JS = """
() => JSON.stringify(Array.from(document.querySelectorAll('.group')).map(g => ({
  label: g.querySelector('.gdomain').textContent,
  meta: g.querySelector('.gmeta').textContent.replace(/\\s+/g, ' ').trim(),
  review: (g.querySelector('.greview') || {}).textContent || '',
  rows: Array.from(g.querySelectorAll('.row')).map(r => {
    var keep = r.querySelector('input[data-keep]') || r.querySelector('input[data-keepmulti]');
    var del = r.querySelector('input[data-del]');
    return {name: r.querySelector('.rname').textContent,
            tags: Array.from(r.querySelectorAll('.tag')).map(t => t.textContent).join('|'),
            keep: keep ? keep.checked : null,
            del: del ? del.checked : null};
  })
})), null, 1)
"""


class App:
    def __init__(self, page):
        self.page = page

    def load(self, fixture):
        self.page.set_input_files("#fileInput", str(FIXTURES / fixture))
        self.page.wait_for_timeout(500)

    @property
    def summary(self):
        return self.page.inner_text("#summary")

    @property
    def notices(self):
        return self.page.inner_text("#notices")

    @property
    def footer(self):
        return self.page.inner_text("#actCount")

    @property
    def groups(self):
        return json.loads(self.page.evaluate(STATE_JS))

    def group(self, label):
        return [g for g in self.groups if g["label"].startswith(label)][0]

    def checked_out(self):
        """Rows the app has marked for deletion, as (group label, entry name)."""
        return [(g["label"], r["name"]) for g in self.groups for r in g["rows"] if r["del"]]


def static_scan():
    src = ARTEFACT.read_text()
    check("static: no absolute URL anywhere in the file", not re.search(r"https?://[a-z0-9]", src, re.I),
          re.findall(r"https?://[a-z0-9]\S*", src, re.I)[:3])
    for token in ["fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "EventSource", "localStorage",
                  "sessionStorage", "indexedDB", "document.cookie", "eval(", "new Function", "serviceWorker",
                  "<iframe", "<link", "<form", "<a ", "src=\"http", "href=\"http", "Worker("]:
        check("static: no %s" % token, token not in src, src.count(token))


def csp_probe(page, console, phase):
    console.clear()
    page.evaluate("""() => {
        var r = {};
        window.__probe = r;
        fetch('http://127.0.0.1:9/probe').then(() => r.fetch = 'resolved').catch(e => r.fetch = 'rejected: ' + e.message);
        try { new WebSocket('ws://127.0.0.1:9/probe'); r.ws = 'constructed'; } catch (e) { r.ws = 'threw'; }
        try { navigator.sendBeacon('http://127.0.0.1:9/probe', 'vault'); r.beacon = 'called'; } catch (e) { r.beacon = 'threw'; }
        var i = new Image(); i.onerror = () => r.img = 'blocked'; i.onload = () => r.img = 'loaded';
        i.src = 'http://127.0.0.1:9/probe.png';
        var s = document.createElement('script'); s.src = 'http://127.0.0.1:9/probe.js';
        document.head.appendChild(s);
    }""")
    page.wait_for_timeout(1200)
    joined = " | ".join(console)
    check("csp: fetch blocked (%s)" % phase, "connect-src 'none'" in joined and "Refused" in joined)
    check("csp: image blocked (%s)" % phase, "img-src data:" in joined)
    check("csp: remote script blocked (%s)" % phase, "script-src" in joined)


def main():
    static_scan()

    with sync_playwright() as p:
        launch = {"args": ["--no-sandbox"], "executable_path": os.environ.get("CHROME_PATH") or None}
        browser = p.chromium.launch(**{k: v for k, v in launch.items() if v is not None})
        ctx = browser.new_context()
        page = ctx.new_page()
        app = App(page)
        requests, console, errors = [], [], []
        page.on("request", lambda r: requests.append(r.url))
        page.on("console", lambda m: console.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(URL)
        check("page: title", page.title() == "Vault duplicate review", page.title())
        check("page: loads no subresource at all",
              page.evaluate("JSON.stringify(performance.getEntriesByType('resource'))") == "[]",
              page.evaluate("JSON.stringify(performance.getEntriesByType('resource'))"))
        check("page: content security policy present",
              "default-src 'none'" in page.evaluate("document.querySelector('meta[http-equiv]').content"))

        # ---- grouping, ranking and preselection ----
        app.load("mixed-vault.json")
        check("mixed: 13 login entries read through cards, notes and trash",
              app.summary.startswith("Read 13 login entries."), app.summary)
        check("mixed: 5 groups, 6 removable, 2 needing a decision",
              "11 of them are copies of 5 entries, so 6 can go" in app.summary and
              "2 groups need a decision" in app.summary, app.summary)
        check("mixed: entries without a stored password are excused in a notice",
              "no stored password" in app.notices, app.notices)

        amz = app.group("amazon.com")
        check("mixed: amazon keeper is the copy holding the authenticator code",
              amz["rows"][0]["keep"] and "authenticator code" in amz["rows"][0]["tags"])
        check("mixed: the two spare amazon copies are marked for deletion",
              sum(1 for r in amz["rows"] if r["del"]) == 2)
        check("mixed: passkey copy beats the newer plain copy",
              app.group("github.com")["rows"][0]["name"] == "GitHub (passkey copy)"
              and app.group("github.com")["rows"][0]["keep"])
        bank = [g for g in app.groups if "passkey and a different copy" in g["review"]]
        check("mixed: split passkey/OTP group preselects nothing",
              bank and not any(r["keep"] or r["del"] for r in bank[0]["rows"]))
        vpn = [g for g in app.groups if "owned by an organization" in g["review"]]
        check("mixed: organization/personal mix is not decided for you",
              vpn and not any(r["keep"] or r["del"] for r in vpn[0]["rows"]))
        router = app.group("Router admin")
        check("mixed: entries with no website match on name and are labelled",
              "matched on entry name" in router["meta"] and router["rows"][0]["keep"])
        check("mixed: four entries preselected in total", app.footer == "4 entries selected for deletion.", app.footer)

        # ---- different services on one parent domain ----
        app.load("parent-domain-only.json")
        pd = app.groups[0]
        check("parentdomain: mail. and vpn. copies are flagged, not decided",
              "parent domain" in pd["review"] and not any(r["keep"] or r["del"] for r in pd["rows"]), pd["review"])
        check("parentdomain: nothing preselected", app.footer == "Nothing selected for deletion.", app.footer)

        # ---- content a copy holds that its twin cannot replace ----
        app.load("custom-fields.json")
        cf = app.groups[0]
        check("fields: differing saved fields are flagged, not decided",
              "saved fields" in cf["review"], cf["review"])
        carrier = [r for r in cf["rows"] if r["name"].startswith("Bank (with")][0]
        check("fields: the copy holding the security answers is not marked for deletion", not carrier["del"])
        check("fields: saved fields and attachments are shown on the row",
              "2 saved fields" in carrier["tags"] and "1 attachment" in carrier["tags"], carrier["tags"])

        # ---- a crafted export ----
        app.load("hostile-entries.json")
        check("hostile: no payload executed",
              page.evaluate("window.__xss === undefined ? 'clean' : 'executed'") == "clean",
              page.evaluate("'window.__xss = ' + String(window.__xss)"))
        check("hostile: no injected element in the results",
              page.evaluate("document.querySelectorAll('#groups img, #groups script, #groups form, "
                            "#groups iframe, #groups textarea').length") == 0)
        check("hostile: entry can not clobber a control id",
              page.evaluate("document.querySelectorAll('[id=clearBtn]').length === 1 && "
                            "document.getElementById('clearBtn').tagName === 'BUTTON'"))
        check("hostile: payload still readable as text",
              any("<img src=x onerror=" in r["name"] for g in app.groups for r in g["rows"]))

        with page.expect_download() as dl:
            page.click("#csvBtn")
        csv_path = pathlib.Path("/tmp") / dl.value.suggested_filename
        dl.value.save_as(str(csv_path))
        csv_text = csv_path.read_text(errors="replace")
        check("csv: formula-leading entry name is neutralised", "'=cmd|'/c calc'!A0" in csv_text,
              [l for l in csv_text.splitlines() if "cmd" in l])
        check("csv: formula-leading username is neutralised", "'@SUM(1+1)" in csv_text)
        check("csv: no cell starts a formula", not re.search(r"(^|,)[=+@]", csv_text, re.M))
        check("csv: quotes inside a value are doubled",
              '"<img src=x onerror=""window.__xss=1"">"' in csv_text)

        with page.expect_download() as dl2:
            page.click("#jsonBtn")
        js_path = pathlib.Path("/tmp") / dl2.value.suggested_filename
        dl2.value.save_as(str(js_path))
        cleaned = json.loads(js_path.read_text())
        removed = json.load(open(FIXTURES / "hostile-entries.json"))["items"]
        check("cleaned json: exactly the marked entries are gone, the rest survive in order",
              [i["id"] for i in cleaned["items"]] == [i["id"] for i in removed if i["id"] not in
                                                      ("11111111-0000-4000-8000-000000000001",
                                                       "33333333-0000-4000-8000-000000000002", "clobber")],
              [i["id"] for i in cleaned["items"]])

        # ---- input validation ----
        app.load("encrypted.json")
        check("input: encrypted export refused with an explanation",
              "This export is encrypted" in page.inner_text("#intake"))
        app.load("not-json.txt")
        check("input: non-JSON refused with an explanation",
              "not valid JSON" in page.inner_text("#intake"))
        app.load("array-root.json")
        check("input: an array-rooted export is accepted", app.summary.startswith("Read 2 login entries."))

        # ---- nothing left the tab ----
        offline_ok = [u for u in requests if not u.startswith("file://")]
        check("network: the only request was for the page itself", offline_ok == [], offline_ok)

        csp_probe(page, console, "after use")

        # ---- runs with the network off ----
        ctx.set_offline(True)
        page.goto(URL)
        app.load("mixed-vault.json")
        check("offline: identical result with no network", app.footer == "4 entries selected for deletion.",
              app.footer)
        ctx.set_offline(False)

        check("runtime: no uncaught page error", errors == [], errors)
        browser.close()

    failed = [c for c in checks if not c[1]]
    print("\n%d checks, %d failed" % (len(checks), len(failed)))
    for name, _, detail in failed:
        print("  FAIL %s  <- %s" % (name, detail))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
