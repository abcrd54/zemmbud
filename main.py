from telegram.ext import Application
from config import BOT_TOKEN, load_cookies
from bot import setup_bot

def main():
    cookies = load_cookies()
    print(f"[CONFIG] {len(cookies)} cookie ter-load dari cookies.txt")
    
    if not BOT_TOKEN:
        print("[ERROR] BOT_TOKEN tidak ditemukan! Buat file .env")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    setup_bot(app, cookies)
    
    print("[BOT] Telegram bot berjalan...")
    print("[BOT] Kirim /start ke bot untuk memulai")
    
    app.run_polling()

if __name__ == "__main__":
    main()
