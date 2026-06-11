import asyncio
from config import load_cookies, get_random_cookie
from scraper import search_posts, comment_on_post

KEYWORD = "wtb samsung a35"
COMMENT = "ready nih, murahin aja gas rekber https://s.shopee.co.id/qh1jGF7pM"

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
    post = result["posts"][0]
    
    print(f"\n[COMMENT] Testing ke post pertama...")
    r = await comment_on_post(browser, browser, post.get("post_url", ""), COMMENT, progress)
    print(f"[COMMENT] {'SUCCESS' if r['success'] else 'FAILED'}: {r['message']}")
    
    try: await browser.stop()
    except: pass

if __name__ == "__main__":
    asyncio.run(main())
