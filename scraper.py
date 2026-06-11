import nodriver as uc
import asyncio
import re
import json

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
        
        search_url = f"https://www.facebook.com/search/groups/?q={keyword.replace(' ', '+')}"
        await report("[PHASE 1] Mencari grup...", 5)
        page = await browser.get(search_url)
        await asyncio.sleep(5)
        
        for _ in range(3):
            await page.scroll_down(1000)
            await asyncio.sleep(1.5)
        
        content = await page.get_content()
        
        group_pattern = re.compile(r'href="(https://www\.facebook\.com/groups/[^"?]+)"')
        group_matches = group_pattern.findall(content)
        
        groups = []
        seen_urls = set()
        seen_names = set()
        
        for href in group_matches:
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            text_match = re.search(rf'href="{re.escape(href)}"[^>]*>([^<]+)', content)
            text = text_match.group(1).strip() if text_match else ""
            
            if text and len(text) > 3 and text not in seen_names:
                seen_names.add(text)
                groups.append({"url": href, "name": text[:80]})
        
        await report(f"  Ditemukan {len(groups)} grup", 10)
        
        max_groups_check = min(len(groups), 20)
        await report(f"[PHASE 2] Cek {max_groups_check} grup...", 10)
        
        approved_groups = []
        checked = 0
        skipped = 0
        
        for group in groups:
            if checked >= max_groups_check:
                break
            if len(approved_groups) >= 10:
                break
                
            checked += 1
            pct = 10 + int((checked / max_groups_check) * 35)
            
            try:
                page = await browser.get(group["url"])
                await asyncio.sleep(4)
                
                for _ in range(2):
                    await page.scroll_down(600)
                    await asyncio.sleep(1)
                
                js_check = """
                (function() {
                    var body = document.body.innerText || '';
                    var lower = body.toLowerCase();
                    
                    if (lower.includes('anda tidak dapat memposting') || lower.includes('you cannot post')) {
                        return 'cannot_post';
                    }
                    if (lower.includes('menunggu persetujuan') || lower.includes('pending approval') || lower.includes('postingan ini menunggu')) {
                        return 'needs_approval';
                    }
                    if (lower.includes('komentar dinonaktifkan') || lower.includes('comments turned off')) {
                        return 'comments_disabled';
                    }
                    if (lower.includes('postingan baru memerlukan persetujuan') || lower.includes('new posts require approval')) {
                        return 'posts_need_approval';
                    }
                    
                    var articles = document.querySelectorAll('[role="article"]');
                    var hasCommentBtn = false;
                    for (var i = 0; i < Math.min(articles.length, 3); i++) {
                        var artText = (articles[i].innerText || '').toLowerCase();
                        if (artText.includes('menunggu persetujuan')) {
                            return 'post_pending';
                        }
                        var commentBtn = articles[i].querySelector('[aria-label="Komentari"], [aria-label="Comment"]');
                        if (commentBtn) {
                            hasCommentBtn = true;
                        }
                    }
                    
                    var commentBox = document.querySelector('[data-lexical-editor="true"][role="textbox"]');
                    if (commentBox) {
                        return 'ok';
                    }
                    
                    if (hasCommentBtn) {
                        return 'ok';
                    }
                    
                    return 'ok';
                })()
                """
                
                check_r = await page.evaluate(js_check)
                
                if check_r == 'ok':
                    approved_groups.append(group)
                    await report(f"  [{checked}] OK {group['name'][:40]}", pct)
                else:
                    skipped += 1
                    await report(f"  [{checked}] SKIP {group['name'][:40]} ({check_r})", pct)
                    
            except Exception as e:
                await report(f"  [{checked}] ERR {group['name'][:40]}", pct)
                continue
        
        await report(f"[PHASE 3] Cari post di {len(approved_groups)} grup...", 50)
        
        all_posts = []
        
        for idx, group in enumerate(approved_groups):
            if len(all_posts) >= 10:
                break
                
            pct = 50 + int(((idx + 1) / len(approved_groups)) * 40)
            
            try:
                page = await browser.get(group["url"])
                await asyncio.sleep(5)
                
                for _ in range(3):
                    await page.scroll_down(800)
                    await asyncio.sleep(1)
                
                keywords_json = json.dumps(keyword_words)
                
                js_code = f"""
                (function() {{
                    var keywords = {keywords_json};
                    var posts = [];
                    var articles = document.querySelectorAll('[role="article"]');
                    for (var i = 0; i < Math.min(articles.length, 20); i++) {{
                        var text = articles[i].innerText || articles[i].textContent || '';
                        text = text.trim().replace(/\\s+/g, ' ').substring(0, 300);
                        if (text.length < 20) continue;
                        
                        var textLower = text.toLowerCase();
                        var matched = false;
                        if (keywords.length === 0) {{
                            matched = true;
                        }} else {{
                            for (var k = 0; k < keywords.length; k++) {{
                                if (textLower.includes(keywords[k])) {{
                                    matched = true;
                                    break;
                                }}
                            }}
                        }}
                        
                        if (!matched) continue;
                        
                        var url = '';
                        var links = articles[i].querySelectorAll('a[href*="/posts/"], a[href*="permalink"], a[href*="story_fbid"]');
                        for (var j = 0; j < links.length; j++) {{
                            var href = links[j].href;
                            if (href && (href.includes('/posts/') || href.includes('permalink') || href.includes('story_fbid'))) {{
                                url = href.split('?')[0];
                                break;
                            }}
                        }}
                        if (!url) {{
                            var allLinks = articles[i].querySelectorAll('a[href]');
                            for (var m = 0; m < allLinks.length; m++) {{
                                var h = allLinks[m].href;
                                if (h && h.includes('facebook.com') && h.includes('/posts/')) {{
                                    url = h.split('?')[0];
                                    break;
                                }}
                            }}
                        }}
                        if (url) {{
                            posts.push({{index: i, text: text, url: url}});
                        }}
                    }}
                    return JSON.stringify(posts);
                }})()
                """
                
                result = await page.evaluate(js_code)
                
                if result:
                    try:
                        posts_data = json.loads(result)
                        
                        for pd in posts_data:
                            if len(all_posts) >= 10:
                                break
                            
                            all_posts.append({
                                "index": len(all_posts) + 1,
                                "article_index": pd["index"],
                                "group": group["name"],
                                "group_url": group["url"],
                                "text": pd["text"],
                                "post_url": pd.get("url", ""),
                            })
                        
                        await report(f"  [{idx+1}] {group['name'][:35]} -> {len(posts_data)} post", pct)
                    except json.JSONDecodeError:
                        await report(f"  [{idx+1}] {group['name'][:35]} -> error", pct)
                else:
                    await report(f"  [{idx+1}] {group['name'][:35]} -> 0 post", pct)
                    
            except Exception as e:
                await report(f"  [{idx+1}] {group['name'][:35]} -> err", pct)
                continue
        
        await report(f"[DONE] {len(all_posts)} post dari {len(approved_groups)} grup", 95)
        
        return {"posts": all_posts, "browser": browser, "page": page}
    
    except Exception as e:
        print(f"Error in search_posts: {e}")
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
        print(f"Error in comment_on_post: {e}")
        return {"success": False, "message": str(e)}
