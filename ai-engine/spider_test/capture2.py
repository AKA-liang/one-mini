"""Quick: headless Playwright → promotionRank → capture ALL product APIs."""
import sys, os, asyncio, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from app.spiders.cookie_manager import get_chanmama_cookie_string, has_chanmama_cookies


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
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        captured.append({"url": url, "body": body})
            except:
                pass

        page.on("response", on_response)

        # Use the URL that actually works (from the browser exploration)
        # Go to promotionRank main page → the SPA will load products via API
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/",
                        wait_until="domcontentloaded", timeout=30000)
        # Wait for SPA to render the product list
        await asyncio.sleep(10)

        cur_url = page.url
        body_text = await page.evaluate("document.body.innerText.substring(0, 2000)")

        print(f"URL: {cur_url[:150]}")
        print(f"Has products in body: {'佣金' in body_text}")
        print(f"Total APIs captured: {len(captured)}")

        # Show product-related APIs
        product_apis = [c for c in captured if "/product/" in c["url"]]
        print(f"\n=== Product APIs ({len(product_apis)}) ===")
        for a in product_apis:
            url_key = a["url"].split("api-service.chanmama.com")[1] if "api-service" in a["url"] else a["url"]
            b = a["body"]
            bs = json.dumps(b, ensure_ascii=False)
            # Extract useful info
            if isinstance(b, list):
                items = b
            elif isinstance(b, dict):
                d = b.get("data")
                if isinstance(d, list):
                    items = d
                elif isinstance(d, dict):
                    items = d.get("list", d.get("data", []))
                else:
                    items = []
            else:
                items = []
            if isinstance(items, list) and items and isinstance(items[0], dict):
                first_keys = list(items[0].keys()) if items else []
                print(f"\n  {url_key[:100]}")
                print(f"  Items: {len(items)}, First keys: {first_keys[:15]}")
                if items:
                    print(f"  Sample: {json.dumps(items[0], ensure_ascii=False)[:500]}")
            else:
                print(f"\n  {url_key[:100]}")
                print(f"  Response: {bs[:300]}")

        await browser.close()

asyncio.run(explore())
