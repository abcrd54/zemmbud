# Facebook Auto Comment Bot

Bot Telegram untuk auto comment post Facebook berdasarkan keyword pencarian.

## Fitur

- Cari post di Facebook berdasarkan keyword
- Auto comment ke post yang ditemukan
- Support multi-cookie (rotasi akun)
- Kontrol via Telegram
- Menggunakan nodriver (undetected chrome) untuk bypass anti-bot

## Instalasi

```bash
pip install -r requirements.txt
```

## Konfigurasi

### 1. Buat file `.env`

```bash
cp .env.example .env
```

Isi dengan Telegram Bot Token:

```
BOT_TOKEN=your_bot_token_here
```

### 2. Isi `cookies.txt`

Masukkan cookie Facebook (satu per baris atau pakai `|`):

```
datr=xxx; sb=xxx; c_user=xxx; xs=xxx; fr=xxx
datr=yyy; sb=yyy; c_user=yyy; xs=yyy; fr=yyy
```

## Cara Mendapatkan Cookie Facebook

1. Login ke Facebook di browser
2. Buka Developer Tools (F12)
3. Tab Application → Cookies
4. Copy semua cookie dan format sesuai contoh di atas

## Jalankan

```bash
python main.py
```

## Penggunaan di Telegram

1. Kirim `/start` ke bot
2. Kirim keyword (contoh: `samsung`)
3. Bot menampilkan post yang ditemukan
4. Kirim komentar yang ingin dipasang
5. Bot mengirim komentar ke semua post

## Command

| Command | Fungsi |
|---------|--------|
| `/start` | Mulai bot |
| `/help` | Bantuan |
| `/reset` | Reset pencarian |

## Catatan

- Gunakan cookie akun tumbal, bukan akun utama
- Jangan terlalu sering menggunakan untuk menghindari spam
- Delay 3-5 detik sudah ditambahkan antar komentar
- Membutuhkan Google Chrome terinstall di sistem
