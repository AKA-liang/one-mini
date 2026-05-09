"""Capture Chanmama rankList API — wait for SPA to fully load."""
import sys, os, asyncio, json
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

        all_apis = {}

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    # Capture any product-related API
                    for tag in ["rankList", "rank_list", "listProduct", "searchProduct", "sameName",
                                "overview", "info", "dealDelivery", "delivery"]:
                        if tag in url and tag not in all_apis:
                            body = await response.json()
                            all_apis[tag] = {"url": url[:200], "json": body}
                            break
            except:
                pass

        page.on("response", on_response)

        # Direct URL approach: use the rank page with keyword in hash/query
        print("Navigating...")
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/?keyword=%E6%89%8B%E6%9C%BA%E5%A3%B3&sortType=sale",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(10)

        # Scroll to trigger lazy loading
        for _ in range(3):
            page.mouse.wheel(0, 800)
            await asyncio.sleep(1)
        await asyncio.sleep(5)

        # Also try typing keyword into search box
        search_input = await page.query_selector('input[placeholder*="搜索"], input[type="text"]')
        if search_input:
            await search_input.click()
            await asyncio.sleep(500)
            await search_input.fill("手机壳")
            await page.keyboard.press("Enter")
            await asyncio.sleep(8)
            print("Typed 手机壳")

        if all_apis:
            for key, data in all_apis.items():
                print(f"\n=== {key} ===")
                print(json.dumps(data["json"], ensure_ascii=False)[:3000])
                print(f"\nURL: {data['url']}")
        else:
            print(f"No APIs captured. URL: {page.url[:150]}")
            body = await page.evaluate("document.body.innerText.substring(0, 1000)")
            print(f"Body:\n{body}")

        await browser.close()

asyncio.run(explore())
