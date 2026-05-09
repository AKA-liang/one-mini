import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def deep_explore():
    print("=" * 60)
    print("Buyin Deep API Capture")
    print("=" * 60)

    all_apis: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        async def handle_response(response):
            url = response.url
            if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".gif", ".avif", ".webp", ".woff2", ".ttf", ".eot"]):
                return
            if "buyin.jinritemai.com" not in url and "fxg.jinritemai.com" not in url:
                return
            if response.status != 200:
                return
            try:
                body = await response.text()
                if not body or len(body) < 50:
                    return
                is_json = False
                try:
                    data = json.loads(body)
                    is_json = True
                except (json.JSONDecodeError, ValueError):
                    pass
                if is_json:
                    all_apis.append({"url": url, "body_len": len(body), "body": body[:5000]})
            except Exception:
                pass

        page.on("response", handle_response)

        print("\n[Navigate] selection square...")
        await page.goto("https://buyin.jinritemai.com/dashboard/service/selection/square", wait_until="networkidle", timeout=60000)
        
        print("[Wait] 10s for SPA to fully render...")
        await page.wait_for_timeout(10000)

        print("[Scroll] Loading more content...")
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(2000)

        print("[Wait] Another 5s...")
        await page.wait_for_timeout(5000)

        # Try clicking on sidebar menu items
        print("[Click] Try sidebar navigation...")
        try:
            sidebar_items = await page.query_selector_all("a[href*='selection'], a[href*='product'], a[href*='goods'], a[href*='rank'], a[href*='hot'], nav a, .menu-item, .nav-item")
            print(f"  Found {len(sidebar_items)} sidebar items")
            for item in sidebar_items[:5]:
                text = (await item.inner_text()).strip()[:30]
                href = await item.get_attribute("href") or ""
                if text:
                    print(f"  Item: text='{text}' href='{href[:60]}'")
        except Exception as e:
            print(f"  Error: {e}")

        print(f"\n[Result] Total JSON APIs captured: {len(all_apis)}")

        # Filter for product-related APIs
        product_keywords = ["product", "goods", "item", "list", "rank", "hot", "recommend", "search", "selection", "commission", "price", "sale", "category"]
        product_apis = []
        for api in all_apis:
            url_lower = api["url"].lower()
            body = api.get("body", "")
            if any(kw in url_lower for kw in product_keywords):
                product_apis.append(api)
            elif len(body) > 200:
                try:
                    data = json.loads(body)
                    if isinstance(data, dict):
                        d = data.get("data", {})
                        if isinstance(d, dict):
                            dkeys = list(d.keys())
                            if any(k in str(dkeys).lower() for k in ["product", "goods", "item", "list", "rank", "commission"]):
                                product_apis.append(api)
                except:
                    pass

        print(f"[Result] Product-related APIs: {len(product_apis)}")

        output_file = OUTPUT_DIR / "buyin_all_apis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_apis, f, ensure_ascii=False, indent=2)
        print(f"Saved all APIs to: {output_file}")

        product_output = OUTPUT_DIR / "buyin_product_apis_v2.json"
        with open(product_output, "w", encoding="utf-8") as f:
            json.dump(product_apis, f, ensure_ascii=False, indent=2)
        print(f"Saved product APIs to: {product_output}")

        # Print summary of interesting APIs
        print("\n=== Interesting API URLs ===")
        seen_urls = set()
        for api in all_apis:
            base_url = api["url"].split("?")[0]
            if base_url not in seen_urls:
                seen_urls.add(base_url)
                print(f"  {api['body_len']:>6} bytes  {base_url}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(deep_explore())
