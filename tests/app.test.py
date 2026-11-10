import json, time
from playwright.sync_api import sync_playwright

import os
URL = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
STUB = """
window.__hits = []; window.__calls = []; window.__rel = []; window.__src = []; window.__offlineCalls = 0;
window.__ctxObj = { lookAhead: 0.1, rawContext: {
  createBuffer: function(ch, len, sr){ var data = []; for (var i = 0; i < ch; i++) data.push(new Float32Array(len));
    return { length: len, sampleRate: sr, numberOfChannels: ch, getChannelData: function(c){ return data[c]; } }; },
  createBufferSource: function(){ return { buffer: null, __g: null, connect: function(g){ this.__g = g; },
    start: function(t){ window.__src.push({ len: this.buffer && this.buffer.length, t: t, gain: this.__g && this.__g.gain }); } }; },
  createGain: function(){ return { gain: { value: 1, calls: [], setTargetAtTime: function(a,b,c){ this.calls.push([a,b,c]); } }, connect: function(){} }; }
} };
(function(){
  function P(v){ return {value:v}; }
  function Base(name){ return class { constructor(o){ window.__built=(window.__built||0)+1; this.ready=Promise.resolve(); this.volume=P(0); this.wet=P(1); this.gain=P(1); this.frequency=P(0); this.Q=P(1); this.n=name; this.o=o; this.off=!!window.__inOffline; }
    connect(){return this} chain(){return this} toDestination(){return this} dispose(){}
    triggerAttackRelease(){ if (this.off) return; var a=[].slice.call(arguments); window.__hits.push(this.n); window.__calls.push({n:this.n,a:a}); }
    triggerRelease(){ if (this.off) return; window.__rel.push(this.n); } } }
  function Failing(name, flag){ var B = Base(name); return class extends B { constructor(o){ if (window[flag]) throw new Error(name + " boom"); super(o); } } }
  window.Tone = {
    start: function(){ return Promise.resolve(); }, now: function(){ return 0; }, immediate: function(){ return window.__now || 0; },
    getContext: function(){ return window.__ctxObj; }, context: {currentTime: 0}, connect: function(){},
    getDestination: function(){ return { connect: function(){} }; },
    Analyser: class { getValue(){ return window.__wave || new Float32Array(2048); } dispose(){} },
    Offline: function(cb, dur){
      window.__offlineCalls++;
      if (window.__failOffline) return Promise.reject(new Error("offline boom"));
      var r; window.__inOffline = true;
      try { r = cb({}); } finally { window.__inOffline = false; }
      var res = Promise.resolve(r);
      return res.then(function(){ return new Promise(function(done){ setTimeout(function(){
        var n = Math.round(dur*48000), chans = [new Float32Array(n), new Float32Array(n)];
        chans[0][10] = window.__probePeak || 0.5; chans[0][11] = -1.2;
        var ab = { numberOfChannels: 2, sampleRate: 48000, length: n, getChannelData: function(c){ return chans[c]; } };
        done({ get: function(){ return ab; }, getChannelData: function(c){ return chans[c]; } });
      }, window.__offlineDelay || 0); }); });
    },
    Transport: { bpm:{value:0}, swing:0, swingSubdivision:"", scheduleRepeat: function(fn){ window.__tick = fn; }, start: function(){}, stop: function(){} },
    Draw: { schedule: function(fn){ fn(); } },
    Limiter: Base("limiter"), Filter: Base("filter"), Gain: Base("gain"), Compressor: Base("comp"), EQ3: Failing("eq", "__failEQ"),
    Reverb: Failing("reverb", "__failReverb"), Distortion: Base("dist"),
    MembraneSynth: Base("mem"), NoiseSynth: Base("noise"), MetalSynth: Failing("metal", "__failMetal")
  };
})();
"""
SR = 48000
LEN = {"kick": 0.9, "snare": 0.9, "rim": 0.35, "clap": 0.9, "tom": 1.0, "hat": 0.35, "open": 1.2, "ride": 2.2, "crash": 4.2}
LANES = ["kick","snare","rim","clap","tom","hat","open","ride","crash"]

def ok(c, label):
    print(("PASS " if c else "FAIL ") + label)
    if not c: raise SystemExit(1)

def newpage(b, errs, flags=None):
    pg = b.new_context(viewport={"width":390,"height":844}).new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    if flags: pg.add_init_script(flags)
    def route(r):
        u = r.request.url
        if "Tone.js" in u: r.fulfill(status=200, content_type="application/javascript", body=STUB)
        elif u.startswith("file://"): r.continue_()
        else: r.abort()
    pg.route("**/*", route)
    pg.goto(URL); pg.wait_for_selector(".cell")
    return pg

def load(pg, js):
    pg.fill("#impText", js); pg.click("#impRead"); pg.wait_for_selector("text=Terbaca")
    pg.click("text=Tambahkan ke lagu")

def audition(pg, i):
    pg.locator(".lane").nth(i).locator(".name").click(); time.sleep(0.12)

errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    page = newpage(b, errs)
    ok(page.inner_text(".ver") == "v0.0.16", "version v0.0.16")
    ok(page.input_value("#kitSel") == "baru" and page.is_checked("#humanize"), "defaults: kit baru, humanize on")

    # ---------- pemanggangan ----------
    audition(page, 0); time.sleep(0.5)
    ok(page.evaluate("window.__offlineCalls") == 1, "kit baru dipanggang dengan satu render offline")
    ok("Suara baru siap" in page.inner_text("#status"), "status: %s" % page.inner_text("#status"))
    page.evaluate("window.__hits.length = 0; window.__src.length = 0")
    for i, nm in enumerate(LANES):
        audition(page, i)
    srcs = page.evaluate("window.__src.map(s => s.len)")
    ok(srcs == [round(LEN[n]*SR) for n in LANES], "tiap lane memutar satu sampel dengan panjang yang benar")
    ok(page.evaluate("window.__hits.length") == 0, "kit baru tidak memicu synth saat bermain (hanya sampel)")
    ok(page.evaluate("window.__src.map(s => s.t)") == [0.005]*9, "audisi: waktu = immediate()+5 ms")

    # ---------- velocity & humanize ----------
    load(page, json.dumps({"sections":[{"name":"v","bars":1,"pattern":{"kick":"X...o...x..............".replace("...x","x")[:16]}}]}))
    page.uncheck("#humanize"); page.click("#playSec")
    page.evaluate("window.__src.length = 0")
    for i in range(16): page.evaluate("window.__tick(0)")
    ok(page.evaluate("window.__src.map(s => s.gain.value)") == [1, 0.4, 0.85], "velocity (aksen/ghost/normal) jadi gain 1 / 0.4 / 0.85")
    page.click("#playSec")
    load(page, json.dumps({"sections":[{"name":"h","bars":4,"pattern":{"kick":"x...x...x...x..."}}]}))
    page.check("#humanize"); page.click("#playSec")
    page.evaluate("window.__src.length = 0")
    for i in range(64): page.evaluate("window.__tick(0)")
    g = page.evaluate("window.__src.map(s => s.gain.value)")
    ok(len(g) == 16 and max(g) <= 0.85 + 1e-9 and min(g) >= 0.85*0.96 - 1e-9 and len(set(g)) > 1, "humanize: 16 pukulan di [%.3f, %.3f]" % (min(g), max(g)))
    page.click("#playSec")

    # ---------- hat tertutup memotong hat terbuka ----------
    load(page, json.dumps({"sections":[{"name":"c","bars":1,"pattern":{"open":".x..............","hat":"..x............."}}]}))
    page.click("#playSec"); page.evaluate("window.__src.length = 0")
    for i in range(3): page.evaluate("window.__tick(0)")
    calls = page.evaluate("(window.__src.find(s => s.len === %d) || {gain:{calls:[]}}).gain.calls" % round(LEN['open']*SR))
    ok(len(calls) == 1 and calls[0][0] == 0, "hat tertutup memotong hat terbuka (gain open ditarik ke 0)")
    page.click("#playSec")

    # ---------- ganti kit tidak membangun apa pun ----------
    built = page.evaluate("window.__built")
    for v in ["lama", "baru", "lama", "baru"]: page.select_option("#kitSel", v)
    ok(page.evaluate("window.__built") == built, "ganti kit tidak membangun node (%d)" % built)
    page.select_option("#kitSel", "lama"); page.evaluate("window.__hits.length = 0; window.__src.length = 0")
    audition(page, 0)
    ok(page.evaluate("window.__hits.slice()") == ["mem"] and page.evaluate("window.__src.length") == 0, "kit lama: satu synth, tanpa sampel")
    page.select_option("#kitSel", "baru")

    # ---------- persistensi ----------
    page.reload(); page.wait_for_selector(".cell")
    ok(page.input_value("#kitSel") == "baru" and page.is_checked("#humanize"), "kit dan humanize tersimpan")
    audition(page, 0); time.sleep(0.4)
    ok(page.evaluate("window.__ctxObj.lookAhead") == 0.3, "lookAhead 0.3 pada konteks bawaan")

    # ---------- kode ekspor ----------
    code = page.inner_text("#code")
    res = page.evaluate("""async (code) => {
      const f = new Function('Tone', code + '; return { song, buildKit };');
      const r = f(window.Tone); const k = await r.buildKit();
      window.__hits.length = 0; Object.keys(k).forEach(id => k[id](0, 1));
      return { ids: Object.keys(k), hits: window.__hits.length, song: r.song.length }; }""", code)
    ok(sorted(res["ids"]) == sorted(LANES) and res["hits"] >= 9, "kode ekspor valid dan jalan")

    # ---------- status tidak dibangun ulang tiap step ----------
    load(page, json.dumps({"sections":[{"name":"s","bars":2,"pattern":{"kick":"x...x...x...x..."}}]}))
    page.click("#playSec"); page.evaluate("window.__tick(0)")
    page.evaluate("window.__mut = 0; new MutationObserver(m => { window.__mut += m.length; }).observe(document.getElementById('status'), {childList:true, characterData:true, subtree:true});")
    for i in range(15): page.evaluate("window.__tick(0)")
    time.sleep(0.1)
    ok(page.evaluate("window.__mut") == 0, "status tidak disentuh dalam bar yang sama")
    page.click("#playSec")

    # ---------- diagnosa ----------
    pg = newpage(b, errs)
    pg.click("#diag summary")
    pg.evaluate("window.__wave = (function(){ var a = new Float32Array(2048); a[100] = 0.5; return a; })()")
    pg.click("#diagMon"); time.sleep(0.2); pg.click("#diagReset"); time.sleep(0.8)
    ok("puncak keluaran: -6.0 dBFS" in pg.inner_text("#diagOut"), "diagnosa: puncak 0.5 = -6.0 dBFS")
    pg.click("#playSec"); pg.evaluate("window.__now = 0.05"); pg.evaluate("window.__tick(0)"); pg.evaluate("window.__now = 0")
    time.sleep(0.8)
    ok("terlambat maks: 50.0 ms" in pg.inner_text("#diagOut"), "diagnosa: keterlambatan 50 ms terdeteksi")
    pg.click("#playSec"); pg.click("#diagMon")
    pg.click("#diagOff"); time.sleep(1.0)
    o = pg.inner_text("#diagOut")
    ok(all(x in o for x in ["kit baru (umum)", "kit baru (padat)", "kit lama (umum)", "kit lama (padat)"]), "diagnosa: uji offline melaporkan 4 kasus")

    # ---------- mode gagal ----------
    # kit baru belum selesai dipanggang -> pakai kit lama dulu, lalu pindah otomatis
    pg = newpage(b, errs, "window.__offlineDelay = 900")
    pg.evaluate("window.__hits.length = 0")
    audition(pg, 0)
    ok(pg.evaluate("window.__hits.slice()") == ["mem"] and pg.evaluate("window.__src.length") == 0, "sebelum selesai dipanggang: kit lama memainkan suara")
    ok("Menyiapkan suara baru" in pg.inner_text("#status"), "status menyiapkan: %s" % pg.inner_text("#status"))
    time.sleep(1.5)
    pg.evaluate("window.__hits.length = 0"); audition(pg, 0)
    ok(pg.evaluate("window.__src.length") >= 1 and pg.evaluate("window.__hits.length") == 0, "setelah selesai: pindah otomatis ke sampel baru")

    # pemanggangan gagal -> kit lama + pesan
    pg = newpage(b, errs, "window.__failOffline = true")
    audition(pg, 0); time.sleep(0.4)
    ok("Kit baru gagal disiapkan" in pg.inner_text("#status"), "bake gagal: pesan tampil: %s" % pg.inner_text("#status")[:60])
    pg.evaluate("window.__hits.length = 0"); audition(pg, 0)
    ok(pg.evaluate("window.__hits.slice()") == ["mem"], "bake gagal: kit lama tetap bersuara")
    pg.click("#playSec"); pg.evaluate("window.__hits.length = 0")
    for i in range(16): pg.evaluate("window.__tick(0)")
    ok(pg.evaluate("window.__hits.length") > 0, "bake gagal: playback tetap jalan")

    # kit baru melempar galat saat dibangun di render offline -> sama
    pg = newpage(b, errs, "window.__failEQ = true")
    audition(pg, 0); time.sleep(0.4)
    ok("Kit baru gagal disiapkan" in pg.inner_text("#status"), "galat saat membangun kit baru: ditangani")

    # reverb gagal dibuat -> pemanggangan tetap selesai
    pg = newpage(b, errs, "window.__failReverb = true")
    audition(pg, 0); time.sleep(0.5)
    ok("Suara baru siap" in pg.inner_text("#status"), "reverb gagal: kit baru tetap siap tanpa ruang")

    # semua kit gagal -> pesan jelas
    pg = newpage(b, errs, "window.__failMetal = true")
    audition(pg, 0); time.sleep(0.3)
    ok("Audio gagal dimulai" in pg.inner_text("#status"), "semua gagal: pesan galat tampil")
    ok(pg.locator(".cell").count() == 144, "semua gagal: halaman utuh")

    ok(errs == [], "tidak ada galat halaman %s" % errs)
    b.close()
