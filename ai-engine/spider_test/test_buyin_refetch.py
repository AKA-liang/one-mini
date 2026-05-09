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

        page = await context.new_page()

        # Capture material_list URLs via response listener (save URL only, not body)
        material_urls = []

        async def on_resp(response):
            url = response.url
            if "material_list" in url and response.status == 200:
                material_urls.append(url)

        page.on("response", on_resp)

        print("[1] Navigate and search...")
        await page.goto("https://buyin.jinritemai.com/dashboard/merch-picking-library", timeout=30000)
        await page.wait_for_timeout(15000)

        # Search
        try:
            search = await page.wait_for_selector(
                "input[placeholder*='搜索'], input[placeholder*='搜'], input[placeholder*='商品'], [class*='search'] input",
                timeout=10000
            )
            if search:
                await search.fill("T恤")
                await page.wait_for_timeout(1000)
                await search.press("Enter")
                await page.wait_for_timeout(15000)
        except:
            print("  No search input")

        # Scroll
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(1500)
        await page.wait_for_timeout(3000)

        print(f"\n  Captured material_list URLs: {len(material_urls)}")

        # Now re-fetch each URL and get the full response
        for idx, url in enumerate(material_urls):
            print(f"\n[2] Re-fetching URL {idx+1}...")
            print(f"  URL: {url[:200]}...")
            result = await page.evaluate("""
                async (url) => {
                    try {
                        const resp = await fetch(url, {credentials: 'include'});
                        const text = await resp.text();
                        try {
                            const data = JSON.parse(text);
                            const promos = data.data?.promotions || [];
                            const promos_pc = data.data?.promotions_pc;
                            const has_more = data.data?.has_more;
                            const extra = data.data?.extra || {};
                            
                            return {
                                status: resp.status,
                                body_length: text.length,
                                total_promotions: promos.length,
                                has_more: has_more,
                                recall_type: extra.recall_type,
                                channel_id: extra.channel_id,
                                promotions_pc_type: typeof promos_pc,
                                promotions_pc_is_list: Array.isArray(promos_pc),
                                promotions_pc_keys: promos_pc && typeof promos_pc === 'object' ? Object.keys(promos_pc).slice(0, 10) : [],
                                first_promo: promos[0] || null,
                                first_promo_keys: promos[0] ? Object.keys(promos[0]) : [],
                            };
                        } catch(e) {
                            return {status: resp.status, body_length: text.length, parse_error: e.message, body_start: text.substring(0, 100)};
                        }
                    } catch(e) {
                        return {error: e.message};
                    }
                }
            """, url)

            print(f"  Result: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

            if result.get("first_promo"):
                output = OUTPUT_DIR / f"buyin_product_structure_{idx}.json"
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"  Saved to: {output}")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
