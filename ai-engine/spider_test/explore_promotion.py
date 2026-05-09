"""Explore Chanmama promotionRank — search + detail pages.
Can we get commission, price, and vendor data here?"""
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

        product_apis = []

        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        body_str = json.dumps(body, ensure_ascii=False)
                        if any(kw in body_str for kw in ["price", "佣金", "commission", "cos",
                                                           "goods", "product", "sale", "达"]):
                            product_apis.append({"url": url[:150], "body": body_str[:1000]})
            except:
                pass

        page.on("response", on_response)

        # ═══ Step 1: Search page with keyword ═══
        print("=== Step 1: PromotionRank search (手机壳) ===")
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/?keyword=手机壳",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(6)

        body = await page.evaluate("document.body.innerText.substring(0, 2000)")
        has_price = "¥" in body or "￥" in body or "到手价" in body
        has_comm = "佣金" in body or "佣金率" in body
        print(f"Has price: {has_price}, Has commission: {has_comm}")
        print(f"Body snippet: {body[:500]}")

        # ═══ Step 2: Look for detail links ═══
        print("\n=== Step 2: Product detail links ===")
        links = await page.evaluate("""
        () => {
            const all = document.querySelectorAll('a[href*="promotionRank/"][href*=".html"]');
            return Array.from(all).slice(0, 5).map(a => ({
                text: (a.textContent || '').trim().substring(0, 60),
                href: a.href || '',
            }));
        }
        """)
        print(f"Found {len(links)} detail links:")
        for l in links:
            print(f"  {l['text'][:50]}")
            print(f"  → {l['href'][:150]}")

        # ═══ Step 3: Visit detail page ═══
        if links:
            detail_url = links[0]["href"]
            print(f"\n=== Step 3: Detail page ===")
            print(f"URL: {detail_url}")
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            detail_body = await page.evaluate("document.body.innerText.substring(0, 3000)")
            has_price = "¥" in detail_body or "￥" in detail_body or "到手价" in detail_body
            has_comm = "佣金" in detail_body
            has_vendor = "达人" in detail_body or "商家" in detail_body
            print(f"Detail — price: {has_price}, commission: {has_comm}, vendor/达人: {has_vendor}")
            print(f"Detail body:\n{detail_body[:1000]}")

        # ═══ Step 4: Show all captured product APIs ═══
        print(f"\n=== Step 4: Captured APIs ({len(product_apis)}) ===")
        seen = set()
        for a in product_apis:
            base = a["url"].split("?")[0]
            if base not in seen:
                seen.add(base)
                print(f"\n  {base[:130]}")
                print(f"  Body: {a['body'][:400]}")

        await browser.close()

asyncio.run(explore())
