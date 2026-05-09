"""
Simple approach: Use Playwright response listener on existing buyin tab.
Just reload the page and capture all network responses.
"""
import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def capture_buyin_apis():
    print("=" * 60)
    print("Buyin API Capture - Simple Reload Approach")
    print("=" * 60)

    all_responses: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]

        # Find existing buyin tab
        buyin_page = None
        for pg in context.pages:
            if "buyin" in pg.url and "selection" in pg.url:
                buyin_page = pg
                break

        if not buyin_page:
            for pg in context.pages:
                if "buyin" in pg.url:
                    buyin_page = pg
                    break

        if not buyin_page:
            buyin_page = await context.new_page()

        print(f"Using page: {buyin_page.url[:80]}")

        async def on_response(response):
            url = response.url
            if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".gif", ".avif", ".webp", ".woff2", ".ttf"]):
                return
            if response.status != 200:
                return
            try:
                body = await response.text()
                if not body or len(body) < 100:
                    return
                # Only save JSON responses
                try:
                    json.loads(body)
                    all_responses.append({"url": url, "status": response.status, "body": body[:8000]})
                except (json.JSONDecodeError, ValueError):
                    pass
            except Exception:
                pass

        buyin_page.on("response", on_response)

        print("\n[Step 1] Reload selection square page...")
        await buyin_page.reload(wait_until="networkidle", timeout=60000)
        print("  Reloaded. Waiting 15s for full render...")
        await buyin_page.wait_for_timeout(15000)

        # Scroll
        print("[Step 2] Scrolling to trigger lazy load...")
        for i in range(8):
            await buyin_page.evaluate("window.scrollBy(0, 800)")
            await buyin_page.wait_for_timeout(1500)

        await buyin_page.wait_for_timeout(5000)

        print(f"\n[Result] Captured {len(all_responses)} JSON responses")

        # Categorize and display
        product_apis = []
        for resp in all_responses:
            url = resp["url"]
            body = resp["body"]
            try:
                data = json.loads(body)
                # Check if this looks like product data
                d = data.get("data", {})
                body_str = body.lower()
                is_product = any(kw in body_str for kw in ["product_name", "goods_name", "title", "commission", "price", "sales", "sku", "item_id", "product_id"])
                is_product_api = any(kw in url.lower() for kw in ["product", "goods", "item", "list", "search", "rank", "recommend", "hot", "selection"])
                
                if is_product or (is_product_api and len(body) > 200):
                    product_apis.append(resp)
            except:
                pass

        print(f"  Product-related: {len(product_apis)}")
        for api in product_apis:
            print(f"  URL: {api['url'][:150]}")
            print(f"  Body({len(api['body'])}): {api['body'][:200]}...")
            try:
                data = json.loads(api["body"])
                d = data.get("data", {})
                if isinstance(d, dict):
                    print(f"  data.keys: {list(d.keys())[:15]}")
                elif isinstance(d, list) and d:
                    print(f"  data: list[{len(d)}], first={str(d[0])[:200]}")
            except:
                pass

        # Save all
        output_file = OUTPUT_DIR / "buyin_reload_captured.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_responses, f, ensure_ascii=False, indent=2)
        print(f"\nAll responses saved to: {output_file}")

        # Also print all unique URL bases
        print("\n=== All Unique API URLs ===")
        seen = set()
        for resp in all_responses:
            base = resp["url"].split("?")[0]
            if base not in seen:
                seen.add(base)
                print(f"  {len(resp['body']):>6}  {base}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(capture_buyin_apis())
