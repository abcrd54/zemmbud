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
                await update.message.reply_text("Cookie belum diisi!")
                return
            
            state["keyword"] = text
            
            progress_msg = await update.message.reply_text(f'Mencari post: "{text}"\n\n[0%] Memulai...')
            
            last_pct = [0]
            
            async def progress_callback(msg, pct=None):
                if pct is not None and pct != last_pct[0]:
                    last_pct[0] = pct
                    bar_len = 10
                    filled = int(bar_len * pct / 100)
                    bar = "=" * filled + "-" * (bar_len - filled)
                    try:
                        await progress_msg.edit_text(
                            f'Mencari post: "{text}"\n\n[{pct}%] [{bar}]'
                        )
                    except:
                        pass
            
            cookie = get_random_cookie(cookies)
            result = await search_posts(text, cookie, progress_callback)
            
            try:
                await progress_msg.delete()
            except:
                pass
            
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
            
            total = len(posts)
            progress_msg = await update.message.reply_text(f"Mengirim komentar ke {total} post...\n\n[0%] Memulai...")
            
            results = []
            for i, post in enumerate(posts):
                pct = int(((i) / total) * 100)
                bar_len = 10
                filled = int(bar_len * pct / 100)
                bar = "=" * filled + "-" * (bar_len - filled)
                
                try:
                    await progress_msg.edit_text(
                        f"Mengirim komentar ke {total} post...\n\n[{pct}%] [{bar}] Post {i+1}/{total}"
                    )
                except:
                    pass
                
                result = await comment_on_post(page, state["browser"], post.get("post_url", ""), text)
                status = "✅" if result["success"] else "❌"
                post_url = post.get("post_url", "")
                url_line = f"\n   {post_url}" if post_url else ""
                results.append(f"{status} Post {post['index']} [{post.get('group', 'N/A')}]: {result['message']}{url_line}")
                
                delay = random.uniform(5, 8)
                await asyncio.sleep(delay)
            
            try:
                await progress_msg.delete()
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
