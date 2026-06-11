import asyncio
import sys
import random
from config import load_cookies, get_random_cookie
from scraper import search_posts, comment_on_post

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

KEYWORD = "iphone"
COMMENT = "ready nih, gas rekber cuy https://s.shopee.co.id/qh1jGF7pM"

async def main():
    cookies = load_cookies()
    if not cookies:
        print("[ERROR] cookies.txt kosong!")
        return
    
    cookie = get_random_cookie(cookies)
    
    async def progress(msg, pct=None):
        if pct is not None:
            print(f"  [{pct}%] {msg}")
        else:
            print(f"  {msg}")
    
    print(f"[TEST] Keyword: {KEYWORD}")
    print(f"[TEST] Words: {KEYWORD.lower().split()}\n")
    
    result = await search_posts(KEYWORD, cookie, progress)
    
    if not result["posts"]:
        print("\n[RESULT] Tidak ada post ditemukan")
        if result["browser"]:
            try: await result["browser"].stop()
            except: pass
        return
    
    print(f"\n[RESULT] {len(result['posts'])} posts:")
    for post in result["posts"]:
        print(f"  {post['index']}. [{post.get('group')}]")
        print(f"     {post['text'][:80]}...")
        print(f"     {post.get('post_url')}")
    
    browser = result["browser"]
    page = result["page"]
    
    posts_to_comment = result["posts"][:5]
    print(f"\n[COMMENT] Mencoba comment ke max {len(posts_to_comment)} post...")
    
    commented = 0
    for i, post in enumerate(posts_to_comment):
        if commented >= 3:
            break
            
        print(f"\n--- Post {i+1}/{len(posts_to_comment)} ---")
        print(f"  URL: {post.get('post_url')}")
        r = await comment_on_post(page, browser, post.get("post_url", ""), COMMENT, progress)
        
        if r.get("skip"):
            print(f"  SKIP: {r['message']}")
            continue
        
        print(f"  Result: {'SUCCESS' if r['success'] else 'FAILED'}: {r['message']}")
        if r['success']:
            commented += 1
        
        if i < len(posts_to_comment) - 1 and commented < 3:
            delay = random.uniform(5, 8)
            print(f"  Waiting {delay:.1f}s...")
            await asyncio.sleep(delay)
    
    print(f"\n[DONE] Berhasil comment ke {commented} post")
    
    try: await browser.stop()
    except: pass

if __name__ == "__main__":
    asyncio.run(main())
