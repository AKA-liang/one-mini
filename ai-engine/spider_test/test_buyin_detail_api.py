import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto("https://buyin.jinritemai.com/dashboard", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        ewid = "346aa0c6226a646c86683d2472ed482e"
        product_ids = ["3659385424289392271", "3692387361779482704", "3697936925378871697"]

        # 1. Try product detail APIs
        print("[1] Try product detail APIs...")
        detail_tests = [
            ("product_detail_v1", f"/pc/selection/product/detail?product_id={product_ids[0]}&ewid={ewid}"),
            ("product_info", f"/pc/selection/product/info?product_id={product_ids[0]}&ewid={ewid}"),
            ("promotion_detail", f"/pc/selection/promotion/detail?promotion_id=3662541158564948304&ewid={ewid}"),
            ("product_card", f"/pc/selection/product/card?product_id={product_ids[0]}&ewid={ewid}"),
            ("goods_detail", f"/api/alliance/goods/detail?product_id={product_ids[0]}"),
            ("alliance_product_detail", f"/api/alliance/product/detail?product_id={product_ids[0]}"),
            ("channel_detail", f"/channel_activity_pc_api/selection_square/product/detail?product_id={product_ids[0]}&ewid={ewid}"),
            ("channel_product", f"/channel_activity_pc_api/selection_square/product?product_id={product_ids[0]}&ewid={ewid}"),
            # Try batch
            ("product_batch", f"/pc/selection/product/batch?product_ids={','.join(product_ids)}&ewid={ewid}"),
            ("promotion_batch", f"/pc/selection/promotion/batch?promotion_ids=3662541158564948304,3692395168763358402&ewid={ewid}"),
        ]

        for name, path in detail_tests:
            url = f"https://buyin.jinritemai.com{path}"
            try:
                result = await page.evaluate("""
                    async (url) => {
                        try {
                            const resp = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
                            const text = await resp.text();
                            return {status: resp.status, body: text.substring(0, 5000)};
                        } catch(e) {
                            return {status: 0, body: e.message};
                        }
                    }
                """, url)
                status = result["status"]
                body = result["body"]
                try:
                    data = json.loads(body)
                    code = data.get("code", data.get("st", "N/A"))
                    print(f"  [{name}] status={status} code={code} len={len(body)}")
                    d = data.get("data", {})
                    if isinstance(d, dict) and d:
                        print(f"    data.keys: {list(d.keys())[:15]}")
                        if any(k in str(d.keys()).lower() for k in ["title", "name", "product"]):
                            for k, v in d.items():
                                if any(nk in k.lower() for nk in ["title", "name", "product_name"]):
                                    print(f"    {k}: {str(v)[:100]}")
                except:
                    print(f"  [{name}] status={status} not JSON len={len(body)} body={body[:100]}")
            except Exception as e:
                print(f"  [{name}] ERROR: {e}")

        # 2. Try material_list with different params that might trigger product data
        print("\n[2] Try material_list variations...")
        mat_tests = [
            ("mat_with_promotion_ids", f"/pc/selection/common/material_list?ewid={ewid}&material_type=promotion_id&recall_type=Sort&page=1&size=20&channel_id=100"),
            ("mat_with_promotion_ids_ch0", f"/pc/selection/common/material_list?ewid={ewid}&material_type=promotion_id&recall_type=Sort&page=1&size=20&channel_id=0"),
            ("mat_product_id_type", f"/pc/selection/common/material_list?ewid={ewid}&material_type=product_id&recall_type=Sort&page=1&size=20"),
            ("mat_search_keyword", f"/pc/selection/common/material_list?ewid={ewid}&keyword=T%E6%81%A4&material_type=promotion_id&recall_type=Search&page=1&size=20"),
            ("mat_search_no_channel", f"/pc/selection/common/material_list?ewid={ewid}&keyword=T%E6%81%A4&recall_type=Search&page=1&size=20"),
            # Try with sence parameter
            ("mat_sence", f"/pc/selection/common/material_list?ewid={ewid}&sence=1&page=1&size=20"),
            # Try search endpoint directly
            ("search_query_v2", f"/pc/selection/search/query?keyword=T%E6%81%A4&page=1&size=20&ewid={ewid}"),
        ]

        for name, path in mat_tests:
            url = f"https://buyin.jinritemai.com{path}"
            try:
                result = await page.evaluate("""
                    async (url) => {
                        try {
                            const resp = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
                            const text = await resp.text();
                            return {status: resp.status, body: text.substring(0, 5000)};
                        } catch(e) {
                            return {status: 0, body: e.message};
                        }
                    }
                """, url)
                status = result["status"]
                body = result["body"]
                try:
                    data = json.loads(body)
                    code = data.get("code", data.get("st", "N/A"))
                    d = data.get("data", {})
                    promos = []
                    if isinstance(d, dict):
                        promos = d.get("promotions", [])
                        print(f"  [{name}] status={status} code={code} promotions={len(promos)}")
                        if promos:
                            pm = promos[0]
                            print(f"    keys: {list(pm.keys())[:15]}")
                            print(f"    data: {json.dumps(pm, ensure_ascii=False)[:300]}")
                except:
                    print(f"  [{name}] status={status} not JSON")
            except Exception as e:
                print(f"  [{name}] ERROR: {e}")

        # 3. Navigate to a product detail page and capture APIs
        print("\n[3] Try navigating to product detail page...")
        all_apis = []

        async def on_resp(response):
            url = response.url
            if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".gif", ".avif", ".webp", ".map"]):
                return
            if response.status != 200:
                return
            try:
                body = await response.text()
                if body and len(body) > 80:
                    try:
                        json.loads(body)
                        all_apis.append({"url": url, "body": body[:15000]})
                    except:
                        pass
            except:
                pass

        context.on("response", on_resp)

        detail_page = await context.new_page()
        await detail_page.goto(f"https://buyin.jinritemai.com/dashboard/merch-picking-library", timeout=30000)
        await detail_page.wait_for_timeout(15000)
        print(f"  Captured: {len(all_apis)} APIs")

        # Try clicking on a product
        try:
            product_card = await detail_page.wait_for_selector(
                "[class*='product'], [class*='goods'], [class*='card'], [class*='item']",
                timeout=5000
            )
            if product_card:
                print("  Found product card, clicking...")
                await product_card.click()
                await detail_page.wait_for_timeout(8000)
                print(f"  After click: {len(all_apis)} APIs")
        except:
            print("  No product card found")

        # Save all APIs from detail page
        if all_apis:
            output = OUTPUT_DIR / "buyin_detail_apis.json"
            with open(output, "w", encoding="utf-8") as f:
                json.dump(all_apis, f, ensure_ascii=False, indent=2)
            print(f"  Saved to: {output}")

            # Show new APIs
            for api in all_apis:
                base = api["url"].split("?")[0]
                if "product" in base.lower() or "detail" in base.lower() or "goods" in base.lower():
                    print(f"    PRODUCT API: {base} ({len(api['body'])} bytes)")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
