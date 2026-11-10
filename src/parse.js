// Parser import drumkode (JSON dan MIDI). Disalin dari blok <parse-start>..<parse-end> di index.html.
// Bergantung pada: STEPS (=16), emptyPattern(), copyPattern() yang didefinisikan app.
  // <parse-start>
  var LANE_ALIAS = {
    kick: "kick", bd: "kick", bassdrum: "kick",
    snare: "snare", sd: "snare",
    rim: "rim", rimshot: "rim", rimclick: "rim", sidestick: "rim", stick: "rim",
    clap: "clap", cp: "clap",
    tom: "tom", toms: "tom", tomtom: "tom", tt: "tom",
    hat: "hat", hihat: "hat", hh: "hat", closedhat: "hat", ch: "hat",
    open: "open", openhat: "open", oh: "open", ohat: "open",
    ride: "ride", rd: "ride",
    crash: "crash", cr: "crash", cc: "crash"
  };
  function normLane(k) {
    return LANE_ALIAS[String(k).toLowerCase().replace(/[^a-z]/g, "")] || null;
  }

  // "x..x" atau [1,0,0,1] -> {steps:[...]} atau {err:"..."}
  function laneToSteps(v) {
    var out = [];
    if (typeof v === "string") {
      var s = v.replace(/[\s|,]/g, "");
      if (s.length !== STEPS) return { err: "panjang " + s.length + " karakter, harus " + STEPS };
      for (var i = 0; i < s.length; i++) {
        var ch = s.charAt(i);
        if ("x1O".indexOf(ch) >= 0) out.push(1);
        else if (ch === "X") out.push(2);
        else if (ch === "o") out.push(3);
        else if (".-_0".indexOf(ch) >= 0) out.push(0);
        else return { err: "karakter '" + ch + "' tidak dikenal (x normal, X aksen, o ghost, . diam)" };
      }
    } else if (Array.isArray(v)) {
      if (v.length !== STEPS) return { err: "array berisi " + v.length + " nilai, harus " + STEPS };
      out = v.map(function (x) {
        var n = Number(x);
        if (x === true) return 1;
        if (n === 2) return 2;
        if (n === 3) return 3;
        return n > 0 ? 1 : 0;
      });
    } else {
      return { err: "harus string 16 karakter atau array 16 angka" };
    }
    return { steps: out };
  }

  function clampNum(raw, min, max, label, warnings) {
    var n = Number(raw);
    if (!isFinite(n)) { warnings.push(label + " tidak valid, diabaikan."); return null; }
    n = Math.round(n);
    var c = Math.min(max, Math.max(min, n));
    if (c !== n) warnings.push(label + " " + n + " di luar " + min + "\u2013" + max + ", dibatasi ke " + c + ".");
    return c;
  }

  // objek {lane: "x..."} -> pola utuh, atau null kalau ada error
  function parsePatternObj(obj, label, errors, warnings, seen) {
    if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
      errors.push(label + ": pola harus berupa objek {lane: \"x...\"}.");
      return null;
    }
    var keys = Object.keys(obj), pat = emptyPattern(), found = 0, bad = 0;
    keys.forEach(function (k) {
      var lane = normLane(k);
      if (!lane) {
        if (!seen[k]) {
          seen[k] = 1;
          warnings.push(label.split(" bar ")[0] + ": lane \"" + k + "\" diabaikan (tersedia: kick, snare, rim, clap, tom, hat, open, ride, crash).");
        }
        return;
      }
      var r = laneToSteps(obj[k]);
      if (r.err) { errors.push(label + " / " + k + ": " + r.err); bad++; return; }
      pat[lane] = r.steps; found++;
    });
    if (keys.length && !found && !bad) { errors.push(label + ": tidak ada lane yang dikenali."); return null; }
    return bad ? null : pat;
  }

  function parseJsonImport(text) {
    var errors = [], warnings = [], d;
    try { d = JSON.parse(text); }
    catch (e) { return { errors: ["JSON tidak valid: " + e.message], warnings: [] }; }
    if (!d || typeof d !== "object" || Array.isArray(d)) {
      return { errors: ["Root harus berupa objek JSON."], warnings: [] };
    }
    if (d.format && d.format !== "drumkode/pattern") {
      warnings.push("format \"" + d.format + "\" tidak dikenal; tetap dicoba dibaca.");
    }
    var rawSecs = Array.isArray(d.sections) ? d.sections : ((d.pattern || d.patterns) ? [d] : null);
    if (!rawSecs || !rawSecs.length) {
      return { errors: ["Tidak ada \"sections\" (atau \"pattern\") di JSON."], warnings: warnings };
    }
    if (rawSecs.length > 32) {
      warnings.push("Hanya 32 section pertama yang dibaca.");
      rawSecs = rawSecs.slice(0, 32);
    }

    var secs = [];
    rawSecs.forEach(function (rs, idx) {
      var label = "section " + (idx + 1);
      if (!rs || typeof rs !== "object") { errors.push(label + ": bukan objek."); return; }
      var name = (typeof rs.name === "string" && rs.name.trim()) ? rs.name.trim().slice(0, 16) : label;
      label = "\"" + name + "\"";
      var seen = {}, pats = [];

      if (Array.isArray(rs.patterns)) {
        if (!rs.patterns.length) { errors.push(label + ": \"patterns\" kosong."); return; }
        var list = rs.patterns;
        if (list.length > 16) {
          warnings.push(label + ": hanya 16 bar pertama yang dibaca.");
          list = list.slice(0, 16);
        }
        if (rs.bars !== undefined && Number(rs.bars) !== list.length) {
          warnings.push(label + ": \"bars\" diabaikan, dipakai jumlah \"patterns\" (" + list.length + ").");
        }
        var okAll = true;
        list.forEach(function (po, bi) {
          var pp = parsePatternObj(po, label + " bar " + (bi + 1), errors, warnings, seen);
          if (!pp) okAll = false; else pats.push(pp);
        });
        if (!okAll) return;
      } else if (rs.pattern !== undefined) {
        var bars = 1;
        if (rs.bars !== undefined) {
          var bn = Number(rs.bars);
          if (!isFinite(bn) || bn < 1) warnings.push(label + ": bars tidak valid, dipakai 1.");
          else {
            bars = Math.min(16, Math.round(bn));
            if (bn > 16) warnings.push(label + ": bars dibatasi 16.");
          }
        }
        var one = parsePatternObj(rs.pattern, label, errors, warnings, seen);
        if (!one) return;
        for (var b = 0; b < bars; b++) pats.push(copyPattern(one));
      } else {
        errors.push(label + ": \"pattern\" atau \"patterns\" tidak ada.");
        return;
      }
      secs.push({ name: name, bars: pats.length, patterns: pats });
    });

    var arr = [];
    if (Array.isArray(d.arrangement) && d.arrangement.length) {
      d.arrangement.slice(0, 128).forEach(function (n) {
        var key = String(n).trim().toLowerCase(), hit = -1;
        for (var i = 0; i < secs.length; i++) {
          if (secs[i].name.toLowerCase() === key) { hit = i; break; }
        }
        if (hit < 0) errors.push("arrangement: section \"" + n + "\" tidak ditemukan.");
        else arr.push(hit);
      });
    } else {
      secs.forEach(function (s, i) { arr.push(i); });
    }

    if (errors.length) return { errors: errors, warnings: warnings };
    return {
      errors: [], warnings: warnings,
      project: {
        name: typeof d.name === "string" ? d.name.slice(0, 40) : "",
        bpm: d.bpm === undefined ? null : clampNum(d.bpm, 60, 180, "bpm", warnings),
        swing: d.swing === undefined ? null : clampNum(d.swing, 0, 60, "swing", warnings),
        sections: secs, arr: arr
      }
    };
  }

  function midiToProject(buf, fileName) {
    var errors = [], warnings = [], dv, p = 0;
    var notes = [], tempo = null, tsig = null, tpb = 0;
    try {
      dv = new DataView(buf);
      if (dv.byteLength < 14 || dv.getUint32(0) !== 0x4D546864) {
        return { errors: ["Bukan file MIDI yang valid."], warnings: [] };
      }
      var hlen = dv.getUint32(4), ntrks = dv.getUint16(10), div = dv.getUint16(12);
      if (div & 0x8000) return { errors: ["MIDI dengan timing SMPTE belum didukung."], warnings: [] };
      tpb = div;
      if (!tpb) return { errors: ["Resolusi MIDI (ticks per beat) tidak valid."], warnings: [] };
      p = 8 + hlen;
      for (var t = 0; t < ntrks; t++) {
        if (p + 8 > dv.byteLength) break;
        if (dv.getUint32(p) !== 0x4D54726B) { errors.push("Struktur track MIDI rusak."); break; }
        var tlen = dv.getUint32(p + 4); p += 8;
        var end = Math.min(p + tlen, dv.byteLength), tick = 0, running = 0, b;
        while (p < end) {
          var delta = 0;
          do { b = dv.getUint8(p++); delta = delta * 128 + (b & 0x7F); } while ((b & 0x80) && p < end);
          tick += delta;
          var st = dv.getUint8(p);
          if (st < 0x80) {
            st = running;
            if (!st) throw new RangeError("running status tanpa status");
          } else {
            p++;
            if (st < 0xF0) running = st;
          }
          if (st === 0xFF) {
            var mt = dv.getUint8(p++), ml = 0;
            do { b = dv.getUint8(p++); ml = ml * 128 + (b & 0x7F); } while ((b & 0x80) && p < end);
            if (mt === 0x51 && ml === 3 && tempo === null) {
              tempo = (dv.getUint8(p) << 16) | (dv.getUint8(p + 1) << 8) | dv.getUint8(p + 2);
            }
            if (mt === 0x58 && ml >= 2 && tsig === null) {
              tsig = { n: dv.getUint8(p), d: Math.pow(2, dv.getUint8(p + 1)) };
            }
            p += ml;
          } else if (st === 0xF0 || st === 0xF7) {
            var sl = 0;
            do { b = dv.getUint8(p++); sl = sl * 128 + (b & 0x7F); } while ((b & 0x80) && p < end);
            p += sl;
          } else {
            var ty = st & 0xF0, ch = st & 0x0F, d1 = dv.getUint8(p++), d2 = 0;
            if (ty !== 0xC0 && ty !== 0xD0) d2 = dv.getUint8(p++);
            if (ty === 0x90 && d2 > 0) notes.push({ tick: tick, ch: ch, note: d1, vel: d2 });
          }
        }
        p = end;
      }
    } catch (e) {
      return { errors: ["File MIDI rusak atau terpotong."], warnings: [] };
    }
    if (errors.length) return { errors: errors, warnings: warnings };

    var drums = notes.filter(function (n) { return n.ch === 9; });
    if (!drums.length && notes.length) {
      drums = notes;
      warnings.push("Tidak ada channel drum (10); semua note dibaca sebagai drum.");
    }
    if (!drums.length) return { errors: ["Tidak ada note di file MIDI."], warnings: warnings };

    var MAP = {
      35: "kick", 36: "kick",
      37: "rim", 38: "snare", 40: "snare", 39: "clap",
      41: "tom", 43: "tom", 45: "tom", 47: "tom", 48: "tom", 50: "tom",
      42: "hat", 44: "hat", 46: "open",
      51: "ride", 53: "ride", 59: "ride",
      49: "crash", 52: "crash", 55: "crash", 57: "crash"
    };
    var sixteenth = tpb / 4, ignored = 0, off = 0, hits = [], maxStep = 0;
    drums.forEach(function (n) {
      var lane = MAP[n.note];
      if (!lane) { ignored++; return; }
      var s = Math.round(n.tick / sixteenth);
      if (Math.abs(n.tick - s * sixteenth) > sixteenth * 0.25) off++;
      hits.push({ lane: lane, step: s, vel: n.vel });
      if (s > maxStep) maxStep = s;
    });
    if (!hits.length) {
      return { errors: ["Tidak ada note drum yang dikenali."], warnings: warnings };
    }
    if (ignored) warnings.push(ignored + " note diabaikan (percussion lain seperti cowbell, tambourine, dll.).");
    if (off) warnings.push(Math.round(off / hits.length * 100) + "% note tidak pas di grid 1/16 (swing/triplet?) dan digeser ke grid terdekat.");
    if (tsig && !(tsig.n === 4 && tsig.d === 4)) {
      warnings.push("Birama " + tsig.n + "/" + tsig.d + ": dibaca sebagai 16 langkah per 4 beat.");
    }

    // velocity -> 3 level: ghost (<=50), normal, aksen (>=110); seragam = semua normal
    var vmin = 127, vmax = 0;
    hits.forEach(function (h) { if (h.vel < vmin) vmin = h.vel; if (h.vel > vmax) vmax = h.vel; });
    var uniform = (vmax - vmin) < 10;
    if (uniform) warnings.push("Velocity di file seragam, semua not dibaca normal (tanpa aksen/ghost).");
    var RANK = { 0: -1, 3: 0, 1: 1, 2: 2 };
    function levelOf(v) { return uniform ? 1 : (v >= 110 ? 2 : (v <= 50 ? 3 : 1)); }

    var barsN = Math.floor(maxStep / STEPS) + 1;
    if (barsN > 32) {
      warnings.push("Dipotong ke 32 bar pertama (file berisi " + barsN + " bar).");
      barsN = 32;
    }
    var barPats = [];
    for (var bi = 0; bi < barsN; bi++) barPats.push(emptyPattern());
    hits.forEach(function (h) {
      var bx = Math.floor(h.step / STEPS);
      if (bx >= barsN) return;
      var cellArr = barPats[bx][h.lane], si = h.step % STEPS, lv = levelOf(h.vel);
      if (RANK[lv] > RANK[cellArr[si]]) cellArr[si] = lv;
    });

    // bar berurutan yang identik digabung jadi satu section
    var runs = [];
    barPats.forEach(function (bp) {
      var key = JSON.stringify(bp), last = runs[runs.length - 1];
      if (last && last.key === key && last.len < 16) last.len++;
      else runs.push({ key: key, len: 1, pat: bp });
    });
    var uniq = {}, secs = [], arr = [];
    var base = (fileName || "midi").replace(/\.[^.]*$/, "").replace(/[^A-Za-z0-9]+/g, " ").trim().slice(0, 12) || "midi";
    runs.forEach(function (r) {
      var k = r.key + "|" + r.len;
      if (uniq[k] === undefined) {
        uniq[k] = secs.length;
        var pats = [];
        for (var q = 0; q < r.len; q++) pats.push(copyPattern(r.pat));
        secs.push({ name: "", bars: r.len, patterns: pats });
      }
      arr.push(uniq[k]);
    });
    secs.forEach(function (s, i) {
      s.name = secs.length === 1 ? base : base + " " + (i < 26 ? String.fromCharCode(65 + i) : "S" + i);
    });

    var bpmV = null;
    if (tempo) bpmV = clampNum(60000000 / tempo, 60, 180, "bpm", warnings);
    return { errors: [], warnings: warnings, project: { name: base, bpm: bpmV, swing: null, sections: secs, arr: arr } };
  }
  // <parse-end>
