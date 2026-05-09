"""Explore Chanmama capabilities — what data is really available?
Runs headless, minimal request rate."""
import sys, os, asyncio, time
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

        # ═══ 1. SPUrank: trending product list ═══
        print("=== 1. SPUrank page (美妆护肤) ===")
        url = "https://www.chanmama.com/SPUrank/?keyword=美妆护肤"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Find product detail links
        links = await page.evaluate("""
        () => {
            const all = document.querySelectorAll('a');
            const found = [];
            for (const a of all) {
                const h = a.href || '';
                const t = (a.textContent || '').trim().substring(0, 60);
                if (h.includes('chanmama.com') && t.length > 3) {
                    found.push({text: t, href: h});
                }
            }
            return found.slice(0, 15);
        }
        """)

        print(f"Relevant links:")
        for l in links:
            print(f"  {l['text'][:50]}")
            print(f"     -> {l['href'][:120]}")

        # Check if there's a product detail link
        detail_links = [l for l in links if "/product/" in l["href"] or "/goods/" in l["href"]]
        print(f"\nPotential product detail links: {len(detail_links)}")

        # ═══ 2. Check page text for commission/price patterns ═══
        body = await page.evaluate("document.body.innerText.substring(0, 3000)")
        has_commission = "佣金" in body or "佣" in body
        has_price = "¥" in body or "￥" in body or "到手价" in body
        print(f"\n=== 2. Data indicators ===")
        print(f"Has ¥ price: {has_price}")
        print(f"Has 佣金: {has_commission}")
        print(f"Body sample: {body[:400]}")

        time.sleep(2)

        # ═══ 3. Try product detail page if available ═══
        if detail_links:
            detail_url = detail_links[0]["href"]
            print(f"\n=== 3. Product detail page ===")
            print(f"URL: {detail_url}")
            await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            detail_body = await page.evaluate("document.body.innerText.substring(0, 3000)")
            has_com = "佣金" in detail_body
            has_pr = "¥" in detail_body or "￥" in detail_body
            print(f"Has ¥ price: {has_pr}")
            print(f"Has 佣金: {has_com}")
            print(f"Page title: {await page.title()}")
            print(f"Detail body sample: {detail_body[:500]}")
        else:
            # If no detail link, try clicking into a product row
            print(f"\n=== 3. Trying to click into first product row ===")
            row_clicked = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('tr, [class*="row"], [class*="item"], [class*="card"]');
                for (const r of rows) {
                    if (r.textContent && r.textContent.length > 20) {
                        r.click();
                        return true;
                    }
                }
                return false;
            }
            """)
            await asyncio.sleep(3)
            print(f"Clicked: {row_clicked}")
            if row_clicked:
                detail_body = await page.evaluate("document.body.innerText.substring(0, 2000)")
                print(f"After click body: {detail_body[:500]}")

        await browser.close()

asyncio.run(explore())
