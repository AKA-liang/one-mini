import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]

        # Use existing page that already has buyin context
        pages = context.pages
        buyin_page = None
        for pg in pages:
            if "buyin" in pg.url:
                buyin_page = pg
                break
        if not buyin_page:
            buyin_page = await context.new_page()
            await buyin_page.goto("https://buyin.jinritemai.com/dashboard", wait_until="networkidle", timeout=30000)
            await buyin_page.wait_for_timeout(5000)

        ewid = "346aa0c6226a646c86683d2472ed482e"

        # Fetch material_list with NO size limit in evaluate
        print("[1] Fetch full material_list...")
        result = await buyin_page.evaluate("""
            async (ewid) => {
                try {
                    const url = `/pc/selection/common/material_list?ewid=${ewid}&channel_id=200&material_type=promotion_id&recall_type=Sort&page=1&size=20`;
                    const resp = await fetch(url, {credentials: 'include'});
                    const text = await resp.text();
                    return {status: resp.status, body: text};
                } catch(e) {
                    return {status: 0, body: e.message};
                }
            }
        """, ewid)

        if result["status"] == 200:
            try:
                data = json.loads(result["body"])
                output = OUTPUT_DIR / "buyin_material_full.json"
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  Saved full material_list to: {output}")

                d = data.get("data", {})
                promos = d.get("promotions", [])
                promos_pc = d.get("promotions_pc")
                has_more = d.get("has_more")
                extra = d.get("extra", {})
                print(f"  promotions: {len(promos)}, has_more: {has_more}")
                print(f"  promotions_pc type: {type(promos_pc).__name__}")

                if promos:
                    pm = promos[0]
                    print(f"  First promo keys: {list(pm.keys())}")
                    print(f"  First promo: {json.dumps(pm, ensure_ascii=False)[:500]}")

                if isinstance(promos_pc, list) and promos_pc:
                    print(f"  promotions_pc count: {len(promos_pc)}")
                    pm = promos_pc[0]
                    print(f"  First promo_pc keys: {list(pm.keys())}")
                    print(f"  First promo_pc: {json.dumps(pm, ensure_ascii=False)[:500]}")

                if isinstance(promos_pc, str):
                    print(f"  promotions_pc is string: {promos_pc[:200]}")

            except json.JSONDecodeError as e:
                print(f"  JSON parse error: {e}")
                print(f"  Body length: {len(result['body'])}")
        else:
            print(f"  status={result['status']}")

        # Also try: search for T恤 on the merch-picking-library page
        print("\n[2] Navigate to picking library and search...")
        page = await context.new_page()

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
                        all_apis.append({"url": url, "body_len": len(body), "body": body[:20000]})
                    except:
                        pass
            except:
                pass

        page.on("response", on_resp)

        await page.goto("https://buyin.jinritemai.com/dashboard/merch-picking-library", timeout=30000)
        await page.wait_for_timeout(15000)

        # Search for T恤
        try:
            search = await page.wait_for_selector(
                "input[placeholder*='搜索'], input[placeholder*='搜'], input[placeholder*='商品'], [class*='search'] input",
                timeout=10000
            )
            if search:
                print("  Typing T恤 and pressing Enter...")
                await search.fill("T恤")
                await page.wait_for_timeout(1000)
                await search.press("Enter")
                await page.wait_for_timeout(15000)
        except:
            print("  No search input found")

        # Scroll
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1500)
        await page.wait_for_timeout(5000)

        print(f"\n  Total APIs: {len(all_apis)}")
        for api in all_apis:
            if any(kw in api["url"].lower() for kw in ["material", "product", "goods", "search", "list", "channel", "detail"]):
                if api["body_len"] > 200:
                    print(f"  {api['body_len']:>6} {api['url'][:150]}")

        # Save all
        output2 = OUTPUT_DIR / "buyin_search_all_apis.json"
        with open(output2, "w", encoding="utf-8") as f:
            json.dump(all_apis, f, ensure_ascii=False, indent=2)
        print(f"  Saved to: {output2}")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
