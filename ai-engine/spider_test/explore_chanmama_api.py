"""Explore Chanmama APIs — what structured data do they return?
Focus: find SPU list API with price, commission, vendor data."""
import sys, os, asyncio, json, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from app.spiders.cookie_manager import get_chanmama_cookie_string, has_chanmama_cookies


async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False)
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

        # Intercept all JSON API responses that contain product data
        product_apis = []

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        body_str = json.dumps(body, ensure_ascii=False)
                        # Only capture APIs that might contain product data
                        if any(kw in body_str for kw in ["spu", "Spu", "SPU", "price", "佣金", "commission",
                                                           "sale", "product", "goods", "达人"]):
                            product_apis.append({
                                "url": url[:150],
                                "body_preview": body_str[:500],
                            })
            except:
                pass

        page.on("response", on_response)

        await page.goto("https://www.chanmama.com/SPUrank/?keyword=美妆护肤", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(10)  # wait for SPA + API calls

        print(f"=== Product-related APIs ({len(product_apis)}) ===")
        for i, a in enumerate(product_apis):
            print(f"\n[{i}] {a['url'][:130]}")
            print(f"    Body: {a['body_preview'][:300]}")

        # Also try one more page — potential product detail with commission
        print("\n\n=== Now try tikGoodsSale page ===")
        product_apis.clear()
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(8)

        print(f"tikGoodsSale APIs: {len(product_apis)}")
        for i, a in enumerate(product_apis[:5]):
            print(f"\n[{i}] {a['url'][:130]}")
            print(f"    Body: {a['body_preview'][:300]}")

        await browser.close()

asyncio.run(explore())
