# uBot AI — Telegram Userbot + Gemini 3.1 Flash-Lite

Stack: Python, Telethon, Gemini API, SQLite, Railway.

## Fitur
- `.onbot`, `.offbot`, `.aistatus`, `.aireset`
- `.pai <pertanyaan>`
- Reply ke pesan AI untuk melanjutkan percakapan
- Mention userbot untuk bertanya
- Memory per user/chat
- `.allow @username`
- `.allow allmember`
- `.allow allmember+admin`
- `.allow grup @username`
- `.allow grup all admin`
- `.allow grup nobody`
- `.mute`, `.unmute`, `.ban`, `.unban` via reply atau @username
- Feedback status untuk mute/unmute/ban/unban

## Permission
- Owner adalah `OWNER_ID`.
- Permission AI di grup bersifat per-user: user tetap harus `.onbot`.
- Permission pengelolaan grup bisa diberikan ke user tertentu atau semua admin.

## Railway
Set environment variables dari `.env.example` di Railway.
Untuk SQLite persisten, mount Railway Volume ke folder project dan gunakan `DB_PATH=/data/ubot.sqlite3`.

## Login Telegram
Untuk production, gunakan `SESSION_STRING` agar restart tidak meminta login ulang. Jika kosong, Telethon akan membuat session file lokal saat login pertama.

## Catatan
Userbot berjalan menggunakan akun Telegram milikmu. Gunakan secara bertanggung jawab dan patuhi aturan Telegram serta kebijakan API yang kamu gunakan.
