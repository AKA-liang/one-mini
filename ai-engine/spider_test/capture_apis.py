"""Simple: navigate promotionRank page, intercept ALL JSON responses, save to file."""
import sys, os, asyncio, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from app.spiders.cookie_manager import get_chanmama_cookie_string, has_chanmama_cookies

OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chanmama_apis.json")


async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        ctx = await browser.new_context(locale="zh-CN")
        if has_chanmama_cookies():
            cs = get_chanmama_cookie_string()
            cookies = []
            for part in cs.split("; "):
                if "=" in part:
                    n, v = part.split("=", 1)
                    cookies.append({"name": n, "value": v, "domain": ".chanmama.com", "path": "/"})
            await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        captured = []

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com/v1/product" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        captured.append({"url": url, "body": body})
            except:
                pass

        page.on("response", on_response)

        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/?keyword=%E6%89%8B%E6%9C%BA%E5%A3%B3",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(12)

        print(f"Page URL: {page.url[:150]}")
        print(f"Captured {len(captured)} product APIs")

        for c in captured[:10]:
            url_key = c["url"].split("?")[0].split("/")[-1]
            body_str = json.dumps(c["body"], ensure_ascii=False)
            print(f"\n--- {url_key} ---")
            print(body_str[:2000])

        # Save all to file
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            clean = []
            for c in captured:
                clean.append({"url": c["url"].split("?")[0], "body": c["body"]})
            json.dump(clean, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(captured)} APIs to {OUT_FILE}")

        await browser.close()

asyncio.run(explore())
