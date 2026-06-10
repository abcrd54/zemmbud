from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import load_cookies, get_random_cookie
from scraper import search_posts, comment_on_post
import asyncio
import random

user_state = {}

def setup_bot(app, cookies):
    
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_state[user_id] = {}
        await update.message.reply_text(
            f"✅ Bot aktif! {len(cookies)} cookie ter-load.\n\n"
            "Kirim keyword untuk cari post di grup Facebook.\n"
            "Contoh: jual hp"
        )
    
    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 Cara penggunaan:\n\n"
            "1. Kirim keyword untuk cari post di grup\n"
            "2. Bot menampilkan post yang ditemukan\n"
            "3. Kirim komentar yang ingin dipasang\n"
            "4. Bot mengirim komentar ke semua post\n\n"
            "Command:\n"
            "/start - Mulai bot\n"
            "/help - Bantuan\n"
            "/reset - Reset pencarian"
        )
    
    async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        state = user_state.get(user_id, {})
        if state.get("browser"):
            try:
                await state["browser"].stop()
            except:
                pass
        user_state[user_id] = {}
        await update.message.reply_text("🔄 State direset. Kirim keyword baru.")
    
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        if user_id not in user_state:
            user_state[user_id] = {}
        
        state = user_state[user_id]
        
        if "keyword" not in state:
            if not cookies:
                await update.message.reply_text("❌ Cookie belum diisi!")
                return
            
            state["keyword"] = text
            await update.message.reply_text(f'🔍 Mencari post di grup: "{text}"...')
            
            cookie = get_random_cookie(cookies)
            result = await search_posts(text, cookie)
            
            if not result["posts"]:
                await update.message.reply_text("❌ Post tidak ditemukan. Coba keyword lain.")
                del state["keyword"]
                return
            
            state["posts"] = result["posts"]
            state["browser"] = result["browser"]
            state["page"] = result["page"]
            
            msg = f"📋 Ditemukan {len(result['posts'])} post di grup:\n\n"
            for post in result["posts"]:
                msg += f"{post['index']}. [{post.get('group', 'N/A')}]\n{post['text'][:100]}...\n\n"
            msg += "💬 Kirim komentar yang ingin dipasang:"
            
            await update.message.reply_text(msg)
            return
        
        if "comment" not in state and state.get("posts") and state.get("page"):
            state["comment"] = text
            posts = state["posts"]
            page = state["page"]
            
            await update.message.reply_text(f"💬 Mengirim komentar ke {len(posts)} post...")
            
            results = []
            for i, post in enumerate(posts):
                result = await comment_on_post(page, post.get("article_index", i), text)
                status = "✅" if result["success"] else "❌"
                results.append(f"{status} Post {post['index']} [{post.get('group', 'N/A')}]: {result['message']}")
                
                delay = random.uniform(3, 5)
                await asyncio.sleep(delay)
            
            if state.get("browser"):
                try:
                    await state["browser"].stop()
                except:
                    pass
            
            success_count = sum(1 for r in results if r.startswith("✅"))
            reply_msg = "\n".join(results) + f"\n\n📊 Hasil: {success_count}/{len(posts)} berhasil"
            reply_msg += "\n\nKirim keyword baru untuk pencarian berikutnya."
            
            await update.message.reply_text(reply_msg)
            del user_state[user_id]
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
