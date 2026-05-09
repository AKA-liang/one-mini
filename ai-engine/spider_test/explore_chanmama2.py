"""Explore Chanmama deeper — headless=False for full SPA render,
intercept API calls for structured data with prices/commissions."""
import sys, os, asyncio, time, json
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

        # Intercept ALL JSON API responses
        api_data = []
        async def on_response(response):
            try:
                url = response.url
                if response.status == 200 and "chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        body_str = json.dumps(body, ensure_ascii=False)[:200]
                        api_data.append({
                            "url": url[:150],
                            "keys": list(body.keys())[:8] if isinstance(body, dict) else "list",
                            "sample": body_str[:100]
                        })
            except:
                pass

        page.on("response", on_response)

        # Navigate to SPUrank
        print("Navigating to SPUrank...")
        await page.goto("https://www.chanmama.com/SPUrank/?keyword=美妆护肤", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)

        # Wait for product table to render
        await page.wait_for_selector("table, [class*='table'], [class*='list']", timeout=15000)
        await asyncio.sleep(3)

        # Extract table data directly
        table_data = await page.evaluate("""
        () => {
            const rows = document.querySelectorAll('table tr, [class*="row"][class*="list"] > div, [class*="item"]');
            const results = [];
            for (const row of rows) {
                const text = (row.textContent || '').trim();
                if (text.length > 20 && text.length < 500) {
                    results.push(text.substring(0, 300));
                }
            }
            return results.slice(0, 10);
        }
        """)

        print(f"\n=== Product rows ({len(table_data)}) ===")
        for i, row in enumerate(table_data):
            print(f"[{i}] {row[:200]}")

        # Show captured API calls
        print(f"\n=== Captured APIs ({len(api_data)}) ===")
        seen_urls = set()
        for a in api_data:
            base = a["url"].split("?")[0]
            if base not in seen_urls:
                seen_urls.add(base)
                print(f"  {a['url'][:120]} keys={a['keys']}")

        # Try clicking into first product row to navigate to detail
        print("\n=== Trying product detail ===")
        try:
            first_product = await page.query_selector("table tr:not(:first-child), [class*='row']")
            if first_product:
                await first_product.click()
                await asyncio.sleep(4)
                detail_url = page.url
                print(f"Detail URL: {detail_url[:200]}")
                detail_body = await page.evaluate("document.body.innerText.substring(0, 2000)")
                # Check for commission/price indicators
                has_comm = "佣金" in detail_body
                has_price = "¥" in detail_body or "￥" in detail_body
                has_达人 = "达人" in detail_body
                print(f"Has price: {has_price}, commission: {has_comm}, 达人: {has_达人}")
                print(f"Detail: {detail_body[:600]}")
        except Exception as e:
            print(f"Click failed: {e}")

        await browser.close()

asyncio.run(explore())
