"""Capture full Chanmama promotionRank API responses.
Focus: v1/product/new/rankList — commission/price/sales data."""
import sys, os, asyncio, json, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
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

        captured = {}

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    key = None
                    if "/product/new/rankList" in url:
                        key = "rankList"
                    elif "/product/new/overview" in url:
                        key = "overview"
                    elif "/product/new/dealDelivery" in url:
                        key = "dealDelivery"
                    elif "/home/product/info" in url:
                        key = "productInfo"
                    if key and key not in captured:
                        body = await response.json()
                        captured[key] = {"url": url[:150], "json": body}
            except:
                pass

        page.on("response", on_response)

        # Navigate to promotionRank search
        print("Navigating to promotionRank search...")
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/?keyword=手机壳&sortType=sale",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(8)

        for key, data in captured.items():
            print(f"\n{'='*60}")
            print(f" API: {key} → {data['url'][:120]}")
            print(f"{'='*60}")
            j = data["json"]
            body_str = json.dumps(j, ensure_ascii=False)
            print(body_str[:3000])

        if not captured:
            print("No target APIs captured. Page URL:", page.url[:120])
            # Try clicking around
            body = await page.evaluate("document.body.innerText.substring(0, 500)")
            print("Body:", body)

        await browser.close()

asyncio.run(explore())
