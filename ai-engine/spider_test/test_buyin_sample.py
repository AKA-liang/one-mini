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

        # Use existing buyin page or create one
        page = None
        for pg in context.pages:
            if "buyin" in pg.url:
                page = pg
                break
        if not page:
            page = await context.new_page()
            await page.goto("https://buyin.jinritemai.com/dashboard", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(5000)

        # Navigate to picking library
        print("[1] Navigate to picking library and search T恤...")
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

        # Now use page.evaluate to fetch material_list and save via Node.js fs
        # Instead, use the response interceptor but save directly to file
        print("\n[2] Fetching material_list via page.evaluate and saving to file...")

        # Save the full response body to a file using the browser's fetch + Blob
        result = await page.evaluate("""
            async () => {
                try {
                    // Get the last material_list URL from performance entries
                    const entries = performance.getEntriesByType('resource');
                    const materialEntries = entries.filter(e => e.name.includes('material_list'));
                    
                    // Re-fetch the last material_list URL
                    let url = null;
                    if (materialEntries.length > 0) {
                        url = materialEntries[materialEntries.length - 1].name;
                    }
                    
                    if (!url) {
                        // Construct a new URL
                        url = window.location.origin + '/pc/selection/common/material_list?channel_id=200&material_type=promotion_id&recall_type=Sort&page=1&size=20';
                    }
                    
                    const resp = await fetch(url, {credentials: 'include'});
                    const text = await resp.text();
                    
                    // Extract just the first few products to understand structure
                    try {
                        const data = JSON.parse(text);
                        const promos = data.data?.promotions || [];
                        const promos_pc = data.data?.promotions_pc;
                        const has_more = data.data?.has_more;
                        
                        // Return structure info + first 3 products
                        const first3 = promos.slice(0, 3);
                        const first3pc = Array.isArray(promos_pc) ? promos_pc.slice(0, 3) : 
                                        (promos_pc && typeof promos_pc === 'object' && promos_pc.list) ? promos_pc.list.slice(0, 3) : [];
                        
                        return {
                            total_promotions: promos.length,
                            has_more: has_more,
                            promotions_pc_type: typeof promos_pc,
                            promotions_pc_count: Array.isArray(promos_pc) ? promos_pc.length : 
                                               (promos_pc && promos_pc.list) ? promos_pc.list.length : 0,
                            sample: first3,
                            sample_pc: first3pc,
                            total_body_length: text.length,
                            url: url
                        };
                    } catch(e) {
                        return {error: e.message, body_length: text.length, url: url};
                    }
                } catch(e) {
                    return {error: e.message};
                }
            }
        """)

        print(f"  Result: {json.dumps(result, ensure_ascii=False, indent=2)[:3000]}")

        # Save sample data
        if result.get("sample"):
            output = OUTPUT_DIR / "buyin_product_sample.json"
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n  Saved sample to: {output}")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
