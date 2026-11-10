# drumkode - contoh aplikasi Android (WebView)

Ini contoh pembungkus (bukan versi stabil). Aplikasi web drumkode (v0.0.16) dijalankan di dalam WebView
dan dilayani dari folder `assets` lewat `WebViewAssetLoader`, jadi localStorage, Web Audio, dan pemilih file bekerja.

Proyek ini ditulis tanpa Android SDK dan internet di sisi pembuat, jadi **belum pernah dikompilasi atau dijalankan**.
Kalau ada galat saat sync atau build, kabari pesannya.

## Cara membuat APK

1. Pasang Android Studio (Koala atau lebih baru).
2. (Disarankan) Unduh Tone.js 14.7.77 ke `app/src/main/assets/Tone.js`
   (lihat `LETAKKAN-Tone.js-DI-SINI.txt`). Tanpa itu aplikasi butuh internet saat dibuka.
3. `File > Open`, pilih folder `android`, biarkan Gradle sync selesai.
4. `Run` (ikon segitiga) ke HP atau emulator, atau `Build > Build APK(s)`.
   Hasilnya ada di `app/build/outputs/apk/debug/app-debug.apk`.
5. Pasang ke HP: salin APK lalu izinkan "install dari sumber tidak dikenal", atau `adb install -r app-debug.apk`.

Lewat terminal: jalankan `gradle wrapper --gradle-version 8.7` sekali (skrip `gradlew` tidak disertakan), lalu `./gradlew assembleDebug`.

## Yang perlu diketahui

- APK debug ditandatangani kunci debug, tidak untuk Play Store. Untuk rilis: tambahkan ikon, signing, dan `isMinifyEnabled`.
- Data (lagu dan pola) tersimpan di localStorage WebView aplikasi ini, **terpisah** dari Chrome. Pindahkan lewat import/ekspor JSON.
- WebView memakai mesin Web Audio yang sama dengan Chrome, jadi kestabilan audio mirip versi web.
  Mesin audio native (mis. Oboe) akan lebih stabil, tetapi itu penulisan ulang.
- Layar dibuat tetap menyala saat aplikasi terbuka (`FLAG_KEEP_SCREEN_ON`); hapus kalau tidak diinginkan.
- Ikon masih ikon bawaan sistem.
