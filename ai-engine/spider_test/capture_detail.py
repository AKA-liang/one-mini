"""SPUrank search → click product → capture detail APIs (commission/price)"""
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

        detail_apis = {}

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    for tag, key in [("overview", "overview"), ("dealDelivery", "deal"), ("info", "info"),
                                      ("delivery", "info"), ("similar", "similar")]:
                        if f"/product/new/{tag}" in url or f"/home/product/{tag}" in url:
                            if key not in detail_apis:
                                detail_apis[key] = {"url": url, "body": await response.json()}
            except:
                pass

        page.on("response", on_response)

        # Step 1: SPUrank search
        print("Step 1: SPUrank search...")
        await page.goto("https://www.chanmama.com/SPUrank/?keyword=手机壳",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Get SPU IDs from API
        spu_links = await page.evaluate("""
        () => {
            const rows = document.querySelectorAll('[class*="row"], [class*="item"], tr');
            for (const r of rows) {
                const links = r.querySelectorAll('a');
                for (const a of links) {
                    const h = a.href || '';
                    if (h.includes('SPUrank') && h.length > 50) return h;
                }
            }
            return '';
        }
        """)
        print(f"SPU detail link: {spu_links[:120]}")

        # Step 2: Click first product to open detail
        print("\nStep 2: Open product detail...")
        if spu_links:
            await page.goto(spu_links, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

        # Step 3: Check detail APIs
        print(f"\nStep 3: Detail APIs captured: {len(detail_apis)}")
        for key, data in detail_apis.items():
            print(f"\n--- {key} ---")
            print(json.dumps(data["body"], ensure_ascii=False)[:2000])

        # Step 4: Also visit a promotionRank detail page
        print("\n\nStep 4: Visit promotionRank detail...")
        await page.goto("https://www.chanmama.com/promotionRank/9o6c-9iWgJZPrbqCFjxC4R7ZWG0G3BXc.html",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Check if new APIs appeared
        for tag, key in [("overview", "overview2"), ("dealDelivery", "deal2"), ("info", "info2")]:
            pass  # These would be captured by on_response

        print(f"Total detail APIs: {len(detail_apis)}")
        for key, data in detail_apis.items():
            print(f"\n--- {key} ---")
            s = json.dumps(data["body"], ensure_ascii=False)
            print(s[:1500])

        await browser.close()

asyncio.run(explore())
