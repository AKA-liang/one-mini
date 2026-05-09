"""Explore Chanmama promotionRank — verify login first, then explore."""
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

        all_apis = []

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        body_str = json.dumps(body, ensure_ascii=False)
                        all_apis.append({"url": url[:150], "keys": list(body.keys())[:8] if isinstance(body, dict) else "N/A"})
            except:
                pass

        page.on("response", on_response)

        # Step 1: Verify login via SPUrank (known working page)
        print("=== Step 1: Verify login (SPUrank) ===")
        await page.goto("https://www.chanmama.com/SPUrank/?keyword=手机壳", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)
        current = page.url
        print(f"SPUrank URL: {current[:120]}")
        logged_in = "register" not in current and "login" not in current
        print(f"Logged in: {logged_in}")

        if not logged_in:
            print("Cookie expired — cannot proceed")
            await browser.close()
            return

        # Step 2: Navigate to promotionRank search
        print("\n=== Step 2: PromotionRank search ===")
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/?keyword=手机壳&sortType=sale",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(6)

        current = page.url
        title = await page.title()
        body = await page.evaluate("document.body.innerText.substring(0, 2000)")
        print(f"URL: {current[:150]}")
        print(f"Title: {title[:100]}")
        print(f"Body has ¥: {'¥' in body or '￥' in body}")
        print(f"Body has 佣金: {'佣金' in body}")
        print(f"Body:\n{body[:800]}")

        # Step 3: Find product detail links
        print("\n=== Step 3: Product links ===")
        links = await page.evaluate("""
        () => {
            const all = document.querySelectorAll('a');
            return Array.from(all).filter(a => {
                const h = a.href || '';
                return h.includes('.html') && h.includes('promotionRank');
            }).slice(0, 5).map(a => ({
                text: (a.textContent || '').trim().substring(0, 80),
                href: a.href || '',
            }));
        }
        """)
        print(f"Detail links: {len(links)}")
        for l in links:
            print(f"  {l['text'][:60]}")
            print(f"  → {l['href'][:150]}")

        # Step 4: Click first product to open detail
        if links:
            print(f"\n=== Step 4: Product detail ===")
            await page.goto(links[0]["href"], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            detail_body = await page.evaluate("document.body.innerText.substring(0, 3000)")
            print(f"Has 佣金: {'佣金' in detail_body}")
            print(f"Has 到手价: {'到手价' in detail_body}")
            print(f"Has ¥: {'¥' in detail_body or '￥' in detail_body}")
            print(f"Detail body:\n{detail_body[:1500]}")

        # Step 5: Show captured APIs
        print(f"\n=== Step 5: APIs ({len(all_apis)}) ===")
        seen = set()
        for a in all_apis:
            base = a["url"].split("?")[0]
            if base not in seen:
                seen.add(base)
                print(f"  {base[:130]} keys={a['keys']}")

        await browser.close()

asyncio.run(explore())
