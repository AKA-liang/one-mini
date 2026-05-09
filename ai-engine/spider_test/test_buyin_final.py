import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    print("=" * 60)
    print("Buyin API Capture - Context-level listener + interaction")
    print("=" * 60)

    all_responses: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]

        # Use CONTEXT-level response handler (captures iframes too!)
        async def on_context_response(response):
            url = response.url
            if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".gif", ".avif", ".webp", ".woff2", ".ttf", ".map", ".mp4", ".mp3"]):
                return
            if response.status != 200:
                return
            try:
                body = await response.text()
                if not body or len(body) < 80:
                    return
                try:
                    json.loads(body)
                    all_responses.append({"url": url, "status": response.status, "body": body[:15000]})
                except (json.JSONDecodeError, ValueError):
                    pass
            except Exception:
                pass

        context.on("response", on_context_response)

        page = await context.new_page()

        # Navigate to picking library
        print("\n[Step 1] Navigate to merch-picking-library...")
        await page.goto("https://buyin.jinritemai.com/dashboard/merch-picking-library", timeout=60000)
        print("  Loaded. Waiting 20s for SPA + micro-frontend to fully render...")
        await page.wait_for_timeout(20000)

        print(f"  Captured so far: {len(all_responses)}")

        # Try to find and interact with search box
        print("\n[Step 2] Look for search input and type...")
        try:
            # Wait for the search input to appear (it's rendered by micro-frontend)
            search_input = await page.wait_for_selector(
                "input[placeholder*='搜索'], input[placeholder*='搜'], input[placeholder*='关键词'], input[placeholder*='商品'], .search-input input, [class*='search'] input, [class*='Search'] input",
                timeout=10000
            )
            if search_input:
                print("  Found search input! Typing 'T恤'...")
                await search_input.fill("T恤")
                await page.wait_for_timeout(1000)
                await search_input.press("Enter")
                print("  Pressed Enter. Waiting 10s for results...")
                await page.wait_for_timeout(10000)
            else:
                print("  No search input found")
        except Exception as e:
            print(f"  Search input not found: {e}")

        # Also try clicking search button
        try:
            search_btn = await page.query_selector("button[class*='search'], [class*='search-btn'], [class*='Search']")
            if search_btn:
                print("  Found search button, clicking...")
                await search_btn.click()
                await page.wait_for_timeout(8000)
        except Exception:
            pass

        # Scroll multiple times
        print("\n[Step 3] Scrolling...")
        for i in range(8):
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1500)

        await page.wait_for_timeout(5000)

        print(f"\n[Step 4] Total captured: {len(all_responses)} JSON responses")

        # Categorize
        product_apis = []
        for resp in all_responses:
            url = resp["url"]
            body = resp["body"].lower()
            # Filter for actual product data
            if any(kw in body for kw in ["product_id", "goods_id", "commission_rate", "product_name", "item_id", "sku_id", "cos_ratio"]):
                product_apis.append(resp)
            elif any(kw in url.lower() for kw in ["product/list", "goods/list", "item/list", "search/result", "picking/list", "selection/list", "recommend/list"]):
                product_apis.append(resp)

        print(f"  Product-related: {len(product_apis)}")

        # Print all unique URLs
        print("\n=== All Unique API URLs ===")
        seen = set()
        for resp in all_responses:
            base = resp["url"].split("?")[0]
            if base not in seen:
                seen.add(base)
                print(f"  {len(resp['body']):>6}  {base}")

        if product_apis:
            print("\n=== PRODUCT DATA APIs ===")
            for api in product_apis:
                print(f"  URL: {api['url'][:150]}")
                print(f"  Body: {api['body'][:500]}")
                print()

        # Save
        output_file = OUTPUT_DIR / "buyin_context_captured.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_responses, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {output_file}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
