"""
Direct API test for Buyin selection product data.
Uses cookies to make direct HTTP requests to known API endpoints.
"""
import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def test_buyin_api_direct():
    print("=" * 60)
    print("Buyin Direct API Test")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        # Create a new page and set cookies from the user-provided data
        page = await context.new_page()

        # First navigate to buyin to set domain context
        print("\n[Step 1] Setting up buyin context...")
        await page.goto("https://buyin.jinritemai.com/dashboard/service/selection/square", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(8000)

        # Now try to trigger product loading via JS fetch in the page context
        print("\n[Step 2] Try fetching product APIs via page context...")
        
        api_tests = [
            # Selection square product list
            {
                "name": "selection_square_list",
                "url": "https://buyin.jinritemai.com/pc/selection_square/product/list?page=1&size=20",
            },
            {
                "name": "selection_product_search",
                "url": "https://buyin.jinritemai.com/pc/selection/product/search?keyword=T%E6%81%A4&page=1&size=20",
            },
            {
                "name": "selection_recommend",
                "url": "https://buyin.jinritemai.com/pc/selection/recommend/list?page=1&size=20",
            },
            {
                "name": "selection_hot",
                "url": "https://buyin.jinritemai.com/pc/selection/hot/list?page=1&size=20",
            },
            {
                "name": "selection_rank",
                "url": "https://buyin.jinritemai.com/pc/selection/rank/list?page=1&size=20",
            },
            {
                "name": "alliance_goods_list",
                "url": "https://buyin.jinritemai.com/api/alliance/goods/list?page=1&size=20",
            },
            {
                "name": "alliance_product_list",
                "url": "https://buyin.jinritemai.com/api/selection/product/list?page=1&size=20",
            },
            # Try the BFF endpoints
            {
                "name": "bff_selection_list",
                "url": "https://buyin.jinritemai.com/bff/selection/product/list?page=1&size=20",
            },
            {
                "name": "selection_square_bff",
                "url": "https://buyin.jinritemai.com/bff/selection_square/list?page=1&size=20",
            },
        ]

        results = []
        for test in api_tests:
            try:
                result = await page.evaluate("""
                    async (url) => {
                        try {
                            const resp = await fetch(url, {
                                credentials: 'include',
                                headers: {
                                    'Accept': 'application/json',
                                }
                            });
                            const text = await resp.text();
                            return { status: resp.status, body: text.substring(0, 3000) };
                        } catch (e) {
                            return { status: 0, body: e.message };
                        }
                    }
                """, test["url"])
                status = result.get("status", 0)
                body = result.get("body", "")
                print(f"  [{test['name']}] status={status} body_len={len(body)}")
                if status == 200 and body:
                    try:
                        data = json.loads(body)
                        print(f"    code={data.get('code', 'N/A')} st={data.get('st', 'N/A')} keys={list(data.keys())[:10]}")
                        d = data.get("data", {})
                        if isinstance(d, dict):
                            print(f"    data keys: {list(d.keys())[:15]}")
                    except json.JSONDecodeError:
                        print(f"    Not JSON: {body[:100]}")
                elif status > 0:
                    print(f"    Response: {body[:200]}")
                results.append({"name": test["name"], "url": test["url"], "status": status, "body": body[:3000]})
            except Exception as e:
                print(f"  [{test['name']}] ERROR: {e}")

        # Save results
        output_file = OUTPUT_DIR / "buyin_api_direct_test.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {output_file}")

        # Also try to check the page DOM for the actual rendered content
        print("\n[Step 3] Check page DOM for product data...")
        dom_check = await page.evaluate("""
            () => {
                const body = document.body.innerText;
                const hasProducts = body.includes('佣金') || body.includes('商品') || body.includes('销量') || body.includes('价格');
                const productCards = document.querySelectorAll('[class*="product"], [class*="goods"], [class*="card"], [class*="item"]');
                return {
                    hasProductKeywords: hasProducts,
                    productCardCount: productCards.length,
                    bodyLength: body.length,
                    bodyPreview: body.substring(0, 2000),
                };
            }
        """)
        print(f"  Has product keywords: {dom_check.get('hasProductKeywords')}")
        print(f"  Product card elements: {dom_check.get('productCardCount')}")
        print(f"  Body length: {dom_check.get('bodyLength')}")
        
        body_preview = dom_check.get("bodyPreview", "")
        if body_preview:
            output_body = OUTPUT_DIR / "buyin_page_text.txt"
            with open(output_body, "w", encoding="utf-8") as f:
                f.write(body_preview)
            print(f"  Saved page text to: {output_body}")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(test_buyin_api_direct())
