import nodriver as uc
import asyncio
import re
import json

async def search_posts(keyword, cookie_str):
    browser = None
    try:
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
        print(f"Searching groups for: {keyword}")
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
        
        print(f"Unique groups found: {len(groups)}")
        
        all_posts = []
        groups_searched = 0
        max_groups = 10
        
        for group in groups:
            if len(all_posts) >= 10:
                break
            
            if groups_searched >= max_groups:
                break
                
            groups_searched += 1
            print(f"\n[{groups_searched}/{max_groups}] Searching: {group['name']}")
            
            try:
                page = await browser.get(group["url"])
                await asyncio.sleep(5)
                
                for _ in range(3):
                    await page.scroll_down(800)
                    await asyncio.sleep(1)
                
                js_code = """
                (function() {
                    var posts = [];
                    var articles = document.querySelectorAll('[role="article"]');
                    for (var i = 0; i < Math.min(articles.length, 10); i++) {
                        var text = articles[i].innerText || articles[i].textContent || '';
                        text = text.trim().replace(/\\s+/g, ' ').substring(0, 200);
                        if (text.length > 20) {
                            posts.push({index: i, text: text});
                        }
                    }
                    return JSON.stringify(posts);
                })()
                """
                
                result = await page.evaluate(js_code)
                
                if result:
                    try:
                        posts_data = json.loads(result)
                        print(f"  Found {len(posts_data)} posts")
                        
                        for pd in posts_data:
                            if len(all_posts) >= 10:
                                break
                            
                            all_posts.append({
                                "index": len(all_posts) + 1,
                                "article_index": pd["index"],
                                "group": group["name"],
                                "group_url": group["url"],
                                "text": pd["text"],
                            })
                            print(f"    Post {len(all_posts)}: {pd['text'][:60]}...")
                    except json.JSONDecodeError:
                        print(f"  Failed to parse JSON")
                else:
                    print(f"  No posts found (might need to join)")
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        return {"posts": all_posts, "browser": browser, "page": page}
    
    except Exception as e:
        print(f"Error in search_posts: {e}")
        if browser:
            try:
                await browser.stop()
            except:
                pass
        return {"posts": [], "browser": None, "page": None}


async def comment_on_post(page, post_index, comment_text):
    try:
        js_click = f"""
        (function() {{
            var articles = document.querySelectorAll('[role="article"]');
            if ({post_index} >= articles.length) return 'not_found';
            articles[{post_index}].click();
            return 'clicked';
        }})()
        """
        
        result = await page.evaluate(js_click)
        
        if result == 'not_found':
            return {"success": False, "message": "Article tidak ditemukan"}
        
        await asyncio.sleep(2)
        
        comment_input = await page.select("[role='textbox'], [contenteditable='true']")
        
        if not comment_input:
            return {"success": False, "message": "Input komentar tidak ditemukan"}
        
        await comment_input.click()
        await asyncio.sleep(0.5)
        await comment_input.send_keys(comment_text)
        await asyncio.sleep(0.5)
        await page.send(uc.cdp.input_.dispatch_event("Enter"))
        await asyncio.sleep(2)
        
        return {"success": True, "message": "Berhasil"}
    
    except Exception as e:
        print(f"Error in comment_on_post: {e}")
        return {"success": False, "message": str(e)}
