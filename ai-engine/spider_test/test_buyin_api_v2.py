"""
Test buyin product APIs by fetching directly from the authenticated page context.
Uses the correct base URLs discovered from the menu.
"""
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
    print("Buyin API Direct Fetch Test")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()

        # Navigate to buyin dashboard to set domain context
        print("[Setup] Navigate to buyin dashboard...")
        await page.goto("https://buyin.jinritemai.com/dashboard", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        # Test various product API endpoints
        api_tests = [
            # Selection search query
            ("search_recommend", "/pc/selection/search/query/recommend"),
            ("search_query", "/pc/selection/search/query?keyword=T恤&page=1&size=20"),
            # Product list endpoints
            ("product_list", "/pc/selection/product/list?page=1&size=20"),
            ("goods_list", "/pc/selection/goods/list?page=1&size=20"),
            # Merch picking hall
            ("merch_picking_list", "/merch-picking-hall/api/product/list?page=1&size=20"),
            ("merch_picking_search", "/merch-picking-hall/api/search?keyword=T恤&page=1&size=20"),
            # Exclusive selection
            ("exclusive_product_list", "/exclusive-selection-square/api/product/list?page=1&size=20"),
            ("exclusive_picking_list", "/exclusive-selection-square/picking/api/list?page=1&size=20"),
            # BFF endpoints
            ("bff_selection", "/bff/selection/product/list?page=1&size=20"),
            ("bff_merch", "/bff/merch-picking/product/list?page=1&size=20"),
            # Common patterns
            ("alliance_product", "/api/alliance/product/list?page=1&size=20"),
            ("selection_product", "/api/selection/product/list?page=1&size=20"),
            # Rank/Hot
            ("rank_list", "/pc/selection/rank/list?page=1&size=20"),
            ("hot_list", "/pc/selection/hot/list?page=1&size=20"),
            # Try with full path
            ("dashboard_selection_list", "/dashboard/api/selection/product/list?page=1&size=20"),
            # Try v2 endpoints
            ("v2_product_list", "/v2/selection/product/list?page=1&size=20"),
            ("v2_goods_list", "/v2/selection/goods/list?page=1&size=20"),
        ]

        results = []
        for name, path in api_tests:
            url = f"https://buyin.jinritemai.com{path}"
            try:
                result = await page.evaluate("""
                    async (url) => {
                        try {
                            const resp = await fetch(url, {
                                credentials: 'include',
                                headers: {'Accept': 'application/json'}
                            });
                            const text = await resp.text();
                            return {status: resp.status, body: text.substring(0, 5000)};
                        } catch(e) {
                            return {status: 0, body: e.message};
                        }
                    }
                """, url)
                status = result.get("status", 0)
                body = result.get("body", "")
                is_json = False
                try:
                    data = json.loads(body)
                    is_json = True
                except:
                    pass
                
                status_icon = "OK" if status == 200 and is_json else "XX"
                print(f"  [{status_icon}] {name}: status={status} len={len(body)}")
                
                if is_json and status == 200:
                    data = json.loads(body)
                    code = data.get("code", data.get("st", "N/A"))
                    print(f"       code={code} keys={list(data.keys())[:8]}")
                    d = data.get("data")
                    if isinstance(d, dict):
                        print(f"       data.keys={list(d.keys())[:12]}")
                    elif isinstance(d, list) and d:
                        print(f"       data: list[{len(d)}]")
                
                results.append({"name": name, "url": url, "status": status, "body": body[:5000]})
            except Exception as e:
                print(f"  [ERR] {name}: {e}")

        # Save
        output_file = OUTPUT_DIR / "buyin_api_direct_v2.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {output_file}")

        await browser.close()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
