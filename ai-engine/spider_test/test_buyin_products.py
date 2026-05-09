import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def explore_buyin_products():
    print("=" * 60)
    print("Buyin Product API Deep Exploration")
    print("=" * 60)

    product_apis: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        async def handle_response(response):
            url = response.url
            if any(kw in url.lower() for kw in ["product", "goods", "item", "search", "selection", "recommend", "list", "rank", "hot"]):
                if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".html", "monitor", "mcs.zijieapi", "vcs.zijieapi", "mon.zijieapi", "tcc?", "btm_mapping", "ab_param", "notice", "announce", "resource", "permission", "login", "account", "anchor", "im/token", "chat/", "feelgood", "config.bytetcc"]):
                    return
                try:
                    body = await response.text()
                    if body and len(body) > 100 and response.status == 200:
                        try:
                            data = json.loads(body)
                            if isinstance(data, dict) and data.get("code") in (0, 200) or data.get("st") == 0:
                                product_apis.append({
                                    "url": url,
                                    "status": response.status,
                                    "body": body[:10000],
                                })
                                print(f"  [PRODUCT API] {url[:150]}")
                                print(f"    keys: {list(data.keys())[:10]}")
                                d = data.get("data", {})
                                if isinstance(d, dict):
                                    print(f"    data keys: {list(d.keys())[:15]}")
                        except (json.JSONDecodeError, ValueError):
                            pass
                except Exception:
                    pass

        page.on("response", handle_response)

        # Step 1: Go to selection square
        print("\n[Step 1] Navigate to selection square...")
        await page.goto("https://buyin.jinritemai.com/dashboard/service/selection/square", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        print(f"  Page: {await page.title()}")
        print(f"  URL: {page.url}")

        # Step 2: Try searching for products
        print("\n[Step 2] Try search input...")
        try:
            search_inputs = await page.query_selector_all("input[type='text'], input[placeholder*='搜索'], input[placeholder*='搜'], input[placeholder*='关键词']")
            print(f"  Found {len(search_inputs)} input fields")
            for i, inp in enumerate(search_inputs):
                placeholder = await inp.get_attribute("placeholder") or ""
                print(f"    input {i}: placeholder='{placeholder}'")
                if any(kw in placeholder for kw in ["搜索", "搜", "关键词", "商品", "search"]):
                    print(f"  Typing 'T恤' into input {i}...")
                    await inp.fill("T恤")
                    await inp.press("Enter")
                    await page.wait_for_timeout(5000)
                    print(f"  After search - URL: {page.url}")
                    break
        except Exception as e:
            print(f"  Search error: {e}")

        # Step 3: Scroll to load more
        print("\n[Step 3] Scroll to trigger lazy loading...")
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(2000)
        print(f"  After scroll - product APIs captured: {len(product_apis)}")

        # Step 4: Click on category tabs if any
        print("\n[Step 4] Click category tabs...")
        try:
            tabs = await page.query_selector_all("[class*='tab'], [class*='category'], [class*='filter'], [class*='cate']")
            print(f"  Found {len(tabs)} tab/filter elements")
            for tab in tabs[:3]:
                text = await tab.inner_text()
                if text and len(text) < 20:
                    print(f"    Clicking tab: {text}")
                    await tab.click()
                    await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  Tab click error: {e}")

        # Step 5: Screenshot
        screenshot_file = OUTPUT_DIR / "buyin_products.png"
        await page.screenshot(path=str(screenshot_file), full_page=False)
        print(f"\nScreenshot: {screenshot_file}")

        # Save product API data
        if product_apis:
            output_file = OUTPUT_DIR / "buyin_product_apis.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(product_apis, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(product_apis)} product APIs to: {output_file}")

        await browser.close()

    print(f"\nTotal product APIs: {len(product_apis)}")


if __name__ == "__main__":
    asyncio.run(explore_buyin_products())
