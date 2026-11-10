import json, time
from playwright.sync_api import sync_playwright

import os
URL = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
STUB = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.test.py"), encoding="utf-8").read().split('STUB = """')[1].split('"""')[0]

STUB = STUB.replace("createBuffer: function(ch, len, sr){ var data = []; for (var i = 0; i < ch; i++) data.push(new Float32Array(len));\n    return { length: len, sampleRate: sr, numberOfChannels: ch, getChannelData: function(c){ return data[c]; } }; },",
                    "createBuffer: function(ch, len, sr){ return new AudioBuffer({ numberOfChannels: ch, length: len, sampleRate: sr }); },")
assert "new AudioBuffer" in STUB

CLAUDE = """
window.__saved = [];
window.claude = { use: async function(n){ if (n === "downloads" && !window.__noDownloads) return { save: async function(r){
  if (window.__declineSave) throw { code: "declined", message: "x" };
  if (window.__failSave) throw { code: "unavailable", message: "x" };
  var txt = null, bytes = null; if (typeof r.data === "string") txt = r.data; else { bytes = Array.from(new Uint8Array(await r.data.arrayBuffer())); } window.__saved.push({ filename: r.filename, data: txt, bytes: bytes }); return { status: "saved" }; } }; return null; } };
"""

def ok(c, label):
    print(("PASS " if c else "FAIL ") + label)
    if not c: raise SystemExit(1)

def newpage(b, errs, init=None, with_claude=True):
    pg = b.new_context(viewport={"width":390,"height":844}, accept_downloads=True).new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    script = (CLAUDE if with_claude else "") + (init or "")
    if script: pg.add_init_script(script)
    def route(r):
        u = r.request.url
        if "Tone.js" in u: r.fulfill(status=200, content_type="application/javascript", body=STUB)
        elif u.startswith("file://"): r.continue_()
        else: r.abort()
    pg.route("**/*", route)
    pg.goto(URL); pg.wait_for_selector(".cell")
    return pg

def saved(pg): return pg.evaluate("window.__saved")

errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = newpage(b, errs)
    ok(pg.inner_text(".ver") == "v0.0.16", "version v0.0.16")
    ok(pg.locator("#expSection").count() == 1 and pg.locator("#expSong").count() == 1 and pg.locator("#expCopy").count() == 1, "tombol ekspor ada")

    # ---- seluruh lagu ----
    code_before = pg.inner_text("#code")
    pg.click("#expSong"); time.sleep(0.2)
    sv = saved(pg)
    ok(len(sv) == 1 and sv[0]["filename"] == "drumkode-lagu-88bpm.json", "lagu: nama file %s" % (sv[0]["filename"] if sv else None))
    song = json.loads(sv[0]["data"])
    ok(song["format"] == "drumkode/pattern" and song["bpm"] == 88 and song["swing"] == 25 and len(song["sections"]) == 4 and len(song["arrangement"]) == 6,
       "lagu: isi JSON lengkap (4 section, 6 entri urutan, bpm, swing)")
    ok("diunduh" in pg.inner_text("#expMsg").lower() or "Diunduh" in pg.inner_text("#expMsg"), "pesan: %s" % pg.inner_text("#expMsg")[:70])

    # ---- bolak-balik: ekspor -> lembar baru -> impor -> sama persis ----
    exported = sv[0]["data"]
    pg.click("#newSheet"); pg.click("#newSheet")
    pg.fill("#impText", exported); pg.click("#impRead"); pg.wait_for_selector("text=Terbaca")
    pg.click("text=Ganti seluruh lagu"); pg.click("text=ketuk lagi untuk mengganti")
    ok(pg.inner_text("#code") == code_before, "bolak-balik: kode Tone.js setelah impor sama persis dengan sebelum ekspor")

    # ---- satu section ----
    pg.click("#tabs .chip:has-text('chorus')")
    pg.click("#expSection"); time.sleep(0.2)
    sv = saved(pg)
    ok(sv[-1]["filename"] == "drumkode-chorus.json", "section: nama file %s" % sv[-1]["filename"])
    one = json.loads(sv[-1]["data"])
    ok(len(one["sections"]) == 1 and one["sections"][0]["name"] == "chorus" and one["arrangement"] == ["chorus"] and one["sections"][0]["bars"] == 4 and "pattern" in one["sections"][0],
       "section: hanya chorus, 4 bar (pola sama = pattern + bars)")

    # ---- pola berbeda per bar -> patterns ----
    pg.uncheck("#linked")
    pg.locator("#bartabs .chip").nth(1).click()
    pg.locator(".lane").nth(8).locator(".cell").nth(0).click()       # crash di bar 2 saja
    pg.click("#expSection"); time.sleep(0.2)
    one = json.loads(saved(pg)[-1]["data"])
    sec = one["sections"][0]
    ok("patterns" in sec and len(sec["patterns"]) == 4 and "crash" in sec["patterns"][1] and "crash" not in sec["patterns"][0], "section: bar berbeda diekspor sebagai patterns")
    # impor kembali section itu (tambahkan) tidak error dan jumlah bar sama
    pg.fill("#impText", saved(pg)[-1]["data"]); pg.click("#impRead"); pg.wait_for_selector("text=Terbaca")
    ok("1 section" in pg.inner_text("#impOut"), "impor ulang file section: terbaca 1 section")

    # ---- nama kembar dibuat unik ----
    pg.click("#newSheet"); pg.click("#newSheet")
    pg.click("#dup")                                  # section 1 dan 'section 1 2'
    pg.fill("#secName", "x")
    pg.click("#tabs .chip >> nth=0"); pg.fill("#secName", "x")
    pg.click("#expSong"); time.sleep(0.2)
    names = [s["name"] for s in json.loads(saved(pg)[-1]["data"])["sections"]]
    ok(len(names) == 2 and names[0] != names[1] and names[0] == "x" and names[1] == "x 2", "nama kembar jadi unik: %s" % names)

    # ---- ditolak oleh pengguna ----
    pg2 = newpage(b, errs, "window.__declineSave = true")
    pg2.click("#expSong"); time.sleep(0.3)
    ok("dibatalkan" in pg2.inner_text("#expMsg"), "ditolak pengguna: pesan dibatalkan, tanpa galat")

    # ---- kapabilitas tidak tersedia: JSON tampil untuk disalin manual ----
    pg3 = newpage(b, errs, "window.__noDownloads = true")
    pg3.click("#expSong"); time.sleep(0.3)
    ok(pg3.is_visible("#expText") and '"format": "drumkode/pattern"' in pg3.input_value("#expText"), "downloads tidak tersedia: JSON ditampilkan untuk disalin")
    ok("tidak tersedia" in pg3.inner_text("#expMsg"), "pesan: %s" % pg3.inner_text("#expMsg")[:80])

    # ---- gagal simpan ----
    pg4 = newpage(b, errs, "window.__failSave = true")
    pg4.click("#expSection"); time.sleep(0.3)
    ok(pg4.is_visible("#expText") and "gagal" in pg4.inner_text("#expMsg").lower(), "gagal simpan: ada jalan keluar manual")

    # ---- browser biasa / WebView (tanpa window.claude): tautan unduhan ----
    pg5 = newpage(b, errs, with_claude=False)
    with pg5.expect_download() as dl:
        pg5.click("#expSong")
    d = dl.value
    ok(d.suggested_filename == "drumkode-lagu-88bpm.json", "tanpa window.claude: unduhan lewat tautan (%s)" % d.suggested_filename)
    txt = open(d.path(), encoding="utf-8").read()
    ok(json.loads(txt)["format"] == "drumkode/pattern", "file yang diunduh berisi JSON valid")

    # ---- salin JSON ----
    pg.click("#expCopy"); time.sleep(0.3)
    ok(("tersalin" in pg.inner_text("#expMsg")) or pg.is_visible("#expText"), "salin JSON: tersalin atau jalan keluar manual")

    ok(errs == [], "tidak ada galat halaman %s" % errs)
    b.close()
