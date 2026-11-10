import io, json, struct, time, zipfile
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_json.test.py"), encoding="utf-8").read().split("errs = []\nwith sync_playwright()")[0])

def parse_midi(data):
    assert data[:4] == b"MThd"
    ppq = int.from_bytes(data[12:14], "big")
    assert data[14:18] == b"MTrk"
    ln = int.from_bytes(data[18:22], "big"); p = 22; end = p + ln
    assert end == len(data), "panjang track tidak cocok"
    t = 0; ons = []; tempo = None; name = None; sig = None; run = 0
    def vlq(p):
        v = 0
        while True:
            b = data[p]; p += 1; v = (v << 7) | (b & 0x7F)
            if not b & 0x80: return v, p
    while p < end:
        d, p = vlq(p); t += d
        st = data[p]
        if st == 0xFF:
            mt = data[p+1]; l, q = vlq(p+2); body = data[q:q+l]; p = q + l
            if mt == 0x51: tempo = int.from_bytes(body, "big")
            if mt == 0x03: name = body.decode()
            if mt == 0x58: sig = tuple(body)
        else:
            p += 1
            ons.append((t, st, data[p], data[p+1])); p += 2
    return ppq, [o for o in ons if o[1] == 0x99 and o[3] > 0], tempo, name, sig

errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = newpage(b, errs)
    ok(pg.inner_text(".ver") == "v0.0.16", "version v0.0.16")
    ok(pg.input_value("#expFmt") == "json" and [o for o in pg.eval_on_selector_all("#expFmt option", "els => els.map(e => e.value)")] == ["json", "midi", "wav"], "pilihan format: json (bawaan), midi, wav")

    def fresh(js):
        pg.click("#newSheet"); pg.click("#newSheet")
        pg.fill("#impText", js); pg.click("#impRead"); pg.wait_for_selector("text=Terbaca")
        pg.click("text=Ganti seluruh lagu"); pg.click("text=ketuk lagi untuk mengganti")

    # ---------------- tidak ada not ----------------
    pg.click("#newSheet"); pg.click("#newSheet")
    pg.select_option("#expFmt", "midi"); pg.click("#expSong")
    ok("Tidak ada not" in pg.inner_text("#expMsg"), "lembar kosong: pesan tidak ada not")

    # ---------------- MIDI ----------------
    song = {"bpm": 120, "swing": 30, "sections": [{"name": "t", "bars": 1, "pattern": {
        "kick": "X...o...x.......", "snare": "....x...........", "hat": ".x.x............"}}]}
    fresh(json.dumps(song))
    pg.select_option("#expFmt", "midi"); pg.click("#expSection"); time.sleep(0.4)
    sv = saved(pg)[-1]
    ok(sv["filename"] == "drumkode-t.zip" and sv["bytes"] is not None, "midi: berkas zip %s" % sv["filename"])
    z = zipfile.ZipFile(io.BytesIO(bytes(sv["bytes"])))
    ok(z.testzip() is None and z.namelist() == ["drumkode-t.mid"], "midi: zip valid (CRC lolos) berisi %s" % z.namelist())
    mid = z.read("drumkode-t.mid")
    ppq, ons, tempo, name, sig = parse_midi(mid)
    got = sorted((t_, n, v) for t_, _, n, v in ons)
    want = sorted([(0, 36, 127), (480, 36, 45), (960, 36, 100), (480, 38, 100), (144, 42, 100), (384, 42, 100)])
    ok(ppq == 480 and tempo == 500000 and name == "drumkode" and sig == (4, 2, 24, 8), "midi: header (480 ppq, 120 bpm, 4/4, nama track)")
    ok(got == want, "midi: not dan velocity benar, swing 30%% menggeser step ganjil: %s" % got)

    # impor kembali file .mid lewat UI aplikasi
    pg.set_input_files("#impFile", files=[{"name": "t.mid", "mimeType": "audio/midi", "buffer": mid}])
    pg.wait_for_selector("text=Terbaca"); pg.click("text=Tambahkan ke lagu")
    kc = pg.locator(".lane").nth(0).locator(".cell"); sc = pg.locator(".lane").nth(1).locator(".cell"); hc = pg.locator(".lane").nth(5).locator(".cell")
    ok([kc.nth(0).get_attribute("data-v"), kc.nth(4).get_attribute("data-v"), kc.nth(8).get_attribute("data-v")] == ["2", "3", "1"], "midi: impor ulang mempertahankan aksen/ghost/normal")
    ok(sc.nth(4).get_attribute("data-v") == "1" and hc.nth(1).get_attribute("data-v") == "1" and hc.nth(3).get_attribute("data-v") == "1", "midi: snare dan hat (step ganjil) kembali ke posisi grid")

    # ---------------- WAV ----------------
    fresh(json.dumps({"bpm": 120, "swing": 0, "sections": [{"name": "w", "bars": 1, "pattern": {"kick": "x...x..........."}}]}))
    pg.select_option("#expFmt", "wav"); pg.click("#expSection")
    ok(pg.is_disabled("#expSong"), "wav: tombol dinonaktifkan selama render")
    for _ in range(40):
        if len(saved(pg)) and saved(pg)[-1]["filename"] == "drumkode-w.zip": break
        time.sleep(0.25)
    sv = saved(pg)[-1]
    ok(sv["filename"] == "drumkode-w.zip", "wav: berkas zip %s" % sv["filename"])
    z = zipfile.ZipFile(io.BytesIO(bytes(sv["bytes"])))
    ok(z.testzip() is None and z.namelist() == ["drumkode-w.wav"], "wav: zip valid berisi %s" % z.namelist())
    w = z.read("drumkode-w.wav")
    ch, sr, bits = struct.unpack("<H", w[22:24])[0], struct.unpack("<I", w[24:28])[0], struct.unpack("<H", w[34:36])[0]
    ok(w[:4] == b"RIFF" and w[8:12] == b"WAVE" and w[12:16] == b"fmt " and struct.unpack("<H", w[20:22])[0] == 1 and ch == 2 and sr == 48000 and bits == 16, "wav: header PCM stereo 48 kHz 16-bit")
    dsize = struct.unpack("<I", w[40:44])[0]
    ok(dsize == len(w) - 44 and struct.unpack("<I", w[4:8])[0] == len(w) - 8, "wav: ukuran data konsisten")
    frames = dsize // 4
    ok(frames >= int(2.0 * 48000), "wav: panjang >= 1 bar pada 120 bpm (%d frame = %.2f dtk)" % (frames, frames / 48000))
    import array
    samples = array.array("h"); samples.frombytes(w[44:44 + dsize])
    left = samples[0::2]
    idx = [i for i, v in enumerate(left) if abs(v) > 300]
    first = idx[0] if idx else -1
    second = next((i for i in idx if i > 12000), -1)
    ok(0 <= first < 60, "wav: pukulan pertama tepat di awal setelah kompensasi latensi (frame %d)" % first)
    ok(abs(second - 24010) < 60, "wav: pukulan kedua tepat di step 4 = 0,5 dtk (frame %d, harapan ~24010)" % second)
    ok(not pg.is_disabled("#expSong"), "wav: tombol aktif lagi setelah selesai")

    # ---------------- ditolak pengguna & tanpa window.claude ----------------
    pg2 = newpage(b, errs, "window.__declineSave = true")
    pg2.select_option("#expFmt", "midi"); pg2.click("#expSong"); time.sleep(0.3)
    ok("dibatalkan" in pg2.inner_text("#expMsg") or "Tidak ada not" in pg2.inner_text("#expMsg"), "midi ditolak/pesan wajar")
    pg3 = newpage(b, errs, with_claude=False)
    pg3.select_option("#expFmt", "midi")
    with pg3.expect_download() as dl:
        pg3.click("#expSong")
    d3 = dl.value
    ok(d3.suggested_filename == "drumkode-lagu-88bpm.zip" and zipfile.ZipFile(d3.path()).testzip() is None, "tanpa window.claude: unduhan zip lewat tautan (%s)" % d3.suggested_filename)

    ok(errs == [], "tidak ada galat halaman %s" % errs)
    b.close()
