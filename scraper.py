import nodriver as uc
import asyncio
import re
import json
import sys
import traceback
from urllib.parse import quote

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RECENT_POSTS_FILTER = "eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D"

async def search_posts(keyword, cookie_str, progress_callback=None):
    browser = None
    try:
        async def report(msg, pct=None):
            print(msg)
            if progress_callback:
                await progress_callback(msg, pct)
        
        keyword_lower = keyword.lower().strip()
        keyword_words = [w.strip() for w in keyword_lower.split() if len(w.strip()) >= 2]
        
        browser = await uc.start(headless=True)
        
        page = await browser.get("https://www.facebook.com/")
        await asyncio.sleep(2)
        
        cookies = cookie_str.split(";")
        for cookie in cookies:
            cookie = cookie.strip()
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                try:
                    await page.send(uc.cdp.network.set_cookie(
                        name=name.strip(),
                        value=value.strip(),
                        domain=".facebook.com",
                        path="/"
                    ))
                except:
                    pass
        
        await page.reload()
        await asyncio.sleep(3)
        
        encoded_keyword = quote(keyword)
        search_url = f"https://www.facebook.com/search/top?q={encoded_keyword}&filters={RECENT_POSTS_FILTER}"
        await report(f"[SEARCH] Mencari post: {keyword}", 10)
        page = await browser.get(search_url)
        await asyncio.sleep(6)
        
        click_r = await page.evaluate("""
        (function() {
            var spans = document.querySelectorAll('span');
            for (var i = 0; i < spans.length; i++) {
                if (spans[i].textContent.trim() === 'Postingan terbaru') {
                    spans[i].click();
                    return 'clicked';
                }
            }
            return 'not_found';
        })()
        """)
        
        if click_r == 'clicked':
            await report("[FILTER] Filter 'Postingan terbaru' diklik", 30)
            await asyncio.sleep(6)
        
        for _ in range(5):
            await page.scroll_down(1000)
            await asyncio.sleep(1.5)
        
        await report("[EXTRACT] Mengambil post dari JSON data...", 50)
        
        content = await page.get_content()
        
        seen_ids = set()
        post_urls = []
        
        for m in re.finditer(r'https?:[/\\]+[/\\]*www\.facebook\.com[/\\]+groups[/\\]+\d+[/\\]+posts[/\\]+(\d+)', content):
            post_id = m.group(1)
            if post_id not in seen_ids:
                seen_ids.add(post_id)
                url = m.group(0).replace("\\/", "/").replace("\\\\", "\\")
                post_urls.append(url)
        
        for m in re.finditer(r'https?:[/\\]+[/\\]*www\.facebook\.com[/\\]+groups[/\\]+\d+[/\\]+permalink[/\\]+(\d+)', content):
            post_id = m.group(1)
            if post_id not in seen_ids:
                seen_ids.add(post_id)
                url = m.group(0).replace("\\/", "/").replace("\\\\", "\\")
                post_urls.append(url)
        
        for m in re.finditer(r'https?:[/\\]+[/\\]*www\.facebook\.com[/\\]+permalink\.php\?story_fbid=([^"&\\]+)&amp;id=(\d+)', content):
            post_id = m.group(1)
            if post_id not in seen_ids:
                seen_ids.add(post_id)
                url = m.group(0).replace("\\/", "/").replace("&amp;", "&")
                post_urls.append(url)
        
        for m in re.finditer(r'https?:[/\\]+[/\\]*www\.facebook\.com[/\\]+([a-zA-Z0-9_.]+)[/\\]+posts[/\\]+([a-zA-Z0-9]+)', content):
            post_id = m.group(2)
            url = m.group(0).replace("\\/", "/")
            if '/search/' not in url and post_id not in seen_ids:
                seen_ids.add(post_id)
                post_urls.append(url)
        
        post_urls = list(post_urls)
        await report(f"  Ditemukan {len(post_urls)} post URL", 60)
        
        all_posts = []
        for url in post_urls[:10]:
            all_posts.append({
                "index": len(all_posts) + 1,
                "group": "",
                "text": "",
                "post_url": url,
            })
        
        await report(f"[DONE] {len(all_posts)} post siap dikomentari", 95)
        
        return {"posts": all_posts, "browser": browser, "page": page}
    
    except Exception as e:
        print("Error in search_posts:")
        traceback.print_exc()
        if browser:
            try:
                await browser.stop()
            except:
                pass
        return {"posts": [], "browser": None, "page": None}


async def comment_on_post(page, browser, post_url, comment_text, progress_callback=None):
    try:
        async def report(msg, pct=None):
            print(msg)
            if progress_callback:
                await progress_callback(msg, pct)
        
        await report(f"  Navigating to post...", None)
        page = await browser.get(post_url)
        await asyncio.sleep(6)
        
        for _ in range(2):
            await page.scroll_down(500)
            await asyncio.sleep(1)
        
        approval_check = await page.evaluate("""
        (function() {
            var body = document.body.innerText || '';
            var lower = body.toLowerCase();
            if (lower.includes('menunggu persetujuan') || lower.includes('pending approval') || lower.includes('postingan ini menunggu')) {
                return 'needs_approval';
            }
            if (lower.includes('komentar dinonaktifkan') || lower.includes('comments turned off')) {
                return 'comments_disabled';
            }
            if (lower.includes('anda tidak dapat memposting') || lower.includes('you cannot post')) {
                return 'cannot_post';
            }
            return 'ok';
        })()
        """)
        
        if approval_check == 'needs_approval':
            return {"success": False, "message": "Grup butuh persetujuan admin", "skip": True}
        elif approval_check == 'comments_disabled':
            return {"success": False, "message": "Komentar dinonaktifkan", "skip": True}
        elif approval_check == 'cannot_post':
            return {"success": False, "message": "Tidak bisa posting", "skip": True}
        
        js_click_comment = """
        (function() {
            var spans = document.querySelectorAll('span');
            for (var i = 0; i < spans.length; i++) {
                var txt = spans[i].textContent.trim().toLowerCase();
                if ((txt === 'comment' || txt === 'komentari' || txt === 'komentar') && spans[i].offsetParent !== null) {
                    spans[i].click();
                    return 'clicked';
                }
            }
            var targets = document.querySelectorAll('[aria-label="Comment"], [aria-label="Komentari"]');
            for (var i = 0; i < targets.length; i++) {
                if (targets[i].offsetParent !== null) {
                    targets[i].click();
                    return 'clicked_aria';
                }
            }
            return 'not_found';
        })()
        """
        
        click_r = await page.evaluate(js_click_comment)
        if click_r == 'not_found':
            return {"success": False, "message": "Comment button tidak ditemukan"}
        
        await asyncio.sleep(3)
        
        js_focus = """
        (function() {
            var editors = document.querySelectorAll('[data-lexical-editor="true"][role="textbox"]');
            for (var i = 0; i < editors.length; i++) {
                if (editors[i].offsetParent !== null) {
                    editors[i].focus();
                    return 'focused';
                }
            }
            var tbs = document.querySelectorAll('[role="textbox"][contenteditable="true"]');
            for (var i = 0; i < tbs.length; i++) {
                if (tbs[i].offsetParent !== null) {
                    tbs[i].focus();
                    return 'focused_tb';
                }
            }
            return 'no_input';
        })()
        """
        
        focus_r = await page.evaluate(js_focus)
        if 'no_input' in focus_r:
            return {"success": False, "message": "Input komentar tidak ditemukan"}
        
        await asyncio.sleep(1)
        
        await page.send(uc.cdp.input_.insert_text(comment_text))
        await asyncio.sleep(2)
        
        await page.send(uc.cdp.input_.dispatch_key_event(type_="keyDown", key="Enter", code="Enter", windows_virtual_key_code=13))
        await asyncio.sleep(0.05)
        await page.send(uc.cdp.input_.dispatch_key_event(type_="keyUp", key="Enter", code="Enter", windows_virtual_key_code=13))
        
        await asyncio.sleep(4)
        
        verify_text = comment_text[0:40]
        js_verify = f"""
        (function() {{
            var bodyText = document.body.innerText || '';
            var lower = bodyText.toLowerCase();
            
            if (lower.includes('menunggu persetujuan') || lower.includes('pending approval')) {{
                return 'pending_approval';
            }}
            
            return bodyText.includes('{verify_text.replace("'", "\\\\'")}') ? 'confirmed' : 'not_visible';
        }})()
        """
        
        verify_r = await page.evaluate(js_verify)
        print(f"  Verify: {verify_r}")
        
        if verify_r == 'confirmed':
            return {"success": True, "message": "Berhasil"}
        elif verify_r == 'pending_approval':
            return {"success": False, "message": "Menunggu persetujuan admin"}
        else:
            return {"success": False, "message": "Gagal verifikasi"}
    
    except Exception as e:
        print("Error in comment_on_post:")
        traceback.print_exc()
        return {"success": False, "message": str(e)}
