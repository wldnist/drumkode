# drumkode

Step sequencer drum di browser, berbasis [Tone.js](https://tonejs.github.io/). Aplikasinya satu berkas (`index.html`), tanpa build.

Dibuat untuk menyusun dan mempelajari pola drum: susun section (intro, verse, chorus), beri pola berbeda tiap bar,
atur urutan lagu, lalu putar, impor, atau ekspor.

## Fitur

- **Grid 16 langkah** dengan 9 lane: kick, snare, rim, clap, tom, hi-hat tertutup dan terbuka, ride, crash.
- **Velocity tiga level** (ghost, normal, aksen): ketuk kotak berulang. Desktop: Shift+klik aksen, Alt+klik ghost, klik kanan hapus.
- **Section dan arrangement:** tiap section punya 1-16 bar, dan tiap bar boleh berpola berbeda. Urutan lagu bebas, section bisa dipakai berulang.
- **Preset** gaya band (rock, half-time, pop-punk, funk, reggae, ska, disco rock, ballad), fill, dan elektronik, plus contoh lagu band.
- **Tempo dan swing.** Swing menggeser langkah 16th ganjil (belum menggeser 8th).
- **Dua kit suara:** "baru" (berlapis, dipanggang jadi sampel saat dimulai) dan "lama" (satu synth per lane). Opsi humanize.
- **Import:** JSON dan MIDI (`.mid`). **Ekspor:** JSON, MIDI, dan WAV (MIDI dan WAV dikemas dalam zip).
- **Kode Tone.js** untuk arrangement penuh dibuat otomatis, termasuk render offline.
- **Panel diagnosa audio:** puncak volume, keterlambatan jadwal, waktu eksekusi step, dan uji clipping offline.

## Menjalankan

Buka `index.html` di Chrome. Butuh internet saat dibuka karena Tone.js dimuat dari cdnjs.
Lagu dan pola tersimpan di `localStorage` browser (kunci `drumkode:v3`).

## Format pola (JSON)

Satu pola = 1 bar 4/4 = 16 langkah (1/16 note). Tiap lane adalah string 16 karakter:
`x` normal, `X` aksen, `o` ghost, `.` diam. Lane: `kick snare rim clap tom hat open ride crash`.

```json
{
  "format": "drumkode/pattern",
  "bpm": 92,
  "sections": [
    { "name": "verse", "bars": 4, "pattern": { "kick": "x.....x.x.......", "snare": "....X..o....X.o.", "hat": "x.x.x.x.x.x.x.x." } },
    { "name": "chorus", "patterns": [
        { "kick": "X.....x.x.......", "crash": "X..............." },
        { "kick": "x.....x.x.......", "ride": "x...x...x...x..." } ] }
  ],
  "arrangement": ["verse", "chorus", "verse", "chorus"]
}
```

- Semua bar sama: `pattern` + `bars`. Tiap bar berbeda: `patterns` (satu objek per bar).
- `bpm` dan `swing` opsional. Lihat contoh lengkap di `patterns/`.

## Struktur

| Path | Isi |
|---|---|
| `index.html` | Aplikasi |
| `src/parse.js` | Parser import JSON dan MIDI, disalin dari blok `<parse-start>..<parse-end>` di `index.html` |
| `patterns/` | Contoh pola. `lama/` berisi hasil dari teks AI yang belum diverifikasi |
| `tests/` | Tes Node dan Python + Playwright (Tone.js di-stub) |
| `archive/` | Versi 0.0.1 yang dibekukan |
| `android/` | Contoh pembungkus WebView (belum pernah dikompilasi), lihat `android/README.md` |

## Tes

```
node tests/parse.test.js
pip install playwright && playwright install chromium
python tests/app.test.py
python tests/export_json.test.py
python tests/export_midi_wav.test.py
```

Tes memakai tiruan Tone.js, jadi yang diuji adalah logika dan alurnya, bukan bunyi. Kualitas suara dan kestabilan audio
tetap perlu dicek langsung di perangkat (gunakan panel Diagnosa audio).

## Catatan teknis

- **Kit baru dipanggang jadi sampel.** Versi awal memicu puluhan node synth per pukulan dan membuat thread utama di HP penuh
  (rata-rata 99,6 ms per step dari jatah 117 ms pada 128 bpm; 22% not terlambat). Setelah dipanggang sekali lewat render offline,
  tiap pukulan hanya satu node pemutar sampel: rata-rata 3,4 ms per step dan 0% terlambat pada pengukuran di Android.
- **Jangan mengganti konteks audio Tone.js** (`Tone.setContext`): `Tone.Transport` terikat ke konteks bawaan, dan versi 0.0.11
  yang menggantinya membuat suara hilang.
- Dialog bawaan browser (`confirm`/`alert`) diblokir di tampilan artifact claude.ai, jadi konfirmasi memakai ketuk dua kali.
- Catatan terbuka: pembacaan puncak keluaran di monitor diagnosa menunjukkan `-inf` pada v0.0.14; belum dijelaskan.

## Riwayat versi

- 0.0.1 sequencer, arrangement, kode Tone.js
- 0.0.2 import JSON dan MIDI
- 0.0.3 pola berbeda per bar, lane rim/tom/ride/crash
- 0.0.4 velocity
- 0.0.5-0.0.8 perbaikan import file dan konfirmasi, tombol lembar baru
- 0.0.9 kit baru, humanize
- 0.0.10 preset band, fill, contoh lagu band
- 0.0.11-0.0.12 upaya stabilitas audio (0.0.11 menyebabkan suara hilang, diperbaiki di 0.0.12)
- 0.0.13 panel diagnosa audio
- 0.0.14 kit baru dipanggang jadi sampel
- 0.0.15 ekspor JSON
- 0.0.16 ekspor MIDI dan WAV (dalam zip)

## Status

Prototipe yang masih berkembang (versi 0.x). Belum ada lisensi.
