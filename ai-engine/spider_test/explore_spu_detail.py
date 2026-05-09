"""Check if SPU detail page shows uncensored price/commission.
Also try SPU detail API endpoints."""
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

        # Capture ALL API responses
        all_apis = []
        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        body_str = json.dumps(body, ensure_ascii=False)
                        all_apis.append({"url": url[:180], "sample": body_str[:400]})
            except:
                pass

        page.on("response", on_response)

        # Navigate to SPU detail page (if we can find the URL pattern)
        spu_id = "ccyfMvKiAIK2ENoJskdmwwbQ-yrhMeYiJcpOGta1wzyCXECHhnoOQ0xYUbvqkX7R"

        # Try different URL patterns for SPU detail
        detail_urls = [
            f"https://www.chanmama.com/SPUrank/?spu_id={spu_id}",
            f"https://www.chanmama.com/SPUrank/detail?spu_id={spu_id}",
            f"https://www.chanmama.com/SPUrank/{spu_id}",
        ]

        for url in detail_urls:
            print(f"\nTrying: {url[:100]}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            body_text = await page.evaluate("document.body.innerText.substring(0, 1000)")
            # Check if this shows anything different
            has_price = "¥" in body_text or "到手价" in body_text or "佣金" in body_text
            print(f"  Price/commission visible: {has_price}")
            if has_price:
                print(f"  Body: {body_text[:500]}")

        # Show all captured API endpoints
        print(f"\n=== All {len(all_apis)} captured APIs ===")
        seen = set()
        for a in all_apis:
            base = a["url"].split("?")[0]
            if base not in seen:
                seen.add(base)
                print(f"  {base[:150]}")

        await browser.close()

asyncio.run(explore())
