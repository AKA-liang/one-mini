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

        # 1. Get the ewid parameter
        ewid_resp = await page.evaluate("""
            async () => {
                const resp = await fetch('/api/hybrid/account/info', {credentials: 'include'});
                return await resp.text();
            }
        """)
        ewid_data = json.loads(ewid_resp)
        # ewid is in the URL params, let's get it from cookies
        ewid = ""
        for cookie_name in ["SASID", "BUYIN_SASID"]:
            val_resp = await page.evaluate(f"""
                () => document.cookie.includes('{cookie_name}') ? document.cookie : ''
            """)
        
        # Actually ewid is generated client-side, let's just use the URL pattern from captured data
        # ewid=346aa0c6226a646c86683d2472ed482e
        ewid = "346aa0c6226a646c86683d2472ed482e"

        # 2. Fetch channel API with full response
        print("[1] Fetching channel API...")
        channel_result = await page.evaluate("""
            async (params) => {
                try {
                    const url = `/channel_activity_pc_api/selection_square/channel?sence=1&new_square=true&ewid=${params.ewid}`;
                    const resp = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
                    const text = await resp.text();
                    return {status: resp.status, body: text};
                } catch(e) {
                    return {status: 0, body: e.message};
                }
            }
        """, {"ewid": ewid})
        print(f"  Channel: status={channel_result['status']} len={len(channel_result['body'])}")

        channel_data = json.loads(channel_result["body"])
        output_file = OUTPUT_DIR / "buyin_channel_full.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(channel_data, f, ensure_ascii=False, indent=2)
        print(f"  Saved to: {output_file}")

        # Parse channel data
        items = channel_data.get("data", {}).get("data", [])
        print(f"  Channel items: {len(items)}")
        for item in items[:3]:
            pmts = item.get("pmts", [])
            print(f"    pmts: {len(pmts)}")
            for pm in pmts[:2]:
                keys = list(pm.keys())
                print(f"      keys: {keys}")
                print(f"      product_id={pm.get('product_id')} price={pm.get('price')} cos_ratio={pm.get('cos_ratio')} cos_fee={pm.get('cos_fee')}")

        # 3. Fetch material_list with different channel_ids
        print("\n[2] Fetching material_list for different channels...")
        for channel_id in ["200", "201", "202", "0", "1"]:
            mat_result = await page.evaluate("""
                async (params) => {
                    try {
                        const url = `/pc/selection/common/material_list?ewid=${params.ewid}&channel_id=${params.channel_id}&material_type=promotion_id&recall_type=Sort&page=1&size=20`;
                        const resp = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
                        const text = await resp.text();
                        return {status: resp.status, body: text};
                    } catch(e) {
                        return {status: 0, body: e.message};
                    }
                }
            """, {"ewid": ewid, "channel_id": channel_id})
            if mat_result["status"] == 200:
                try:
                    mat_data = json.loads(mat_result["body"])
                    promos = mat_data.get("data", {}).get("promotions", [])
                    has_more = mat_data.get("data", {}).get("has_more")
                    print(f"  channel_id={channel_id}: promotions={len(promos)} has_more={has_more}")
                    if promos:
                        pm = promos[0]
                        print(f"    first promo keys: {list(pm.keys())[:15]}")
                        print(f"    first promo: {json.dumps(pm, ensure_ascii=False)[:300]}")
                        output_file2 = OUTPUT_DIR / f"buyin_material_ch{channel_id}.json"
                        with open(output_file2, "w", encoding="utf-8") as f:
                            json.dump(mat_data, f, ensure_ascii=False, indent=2)
                except:
                    print(f"  channel_id={channel_id}: parse error, len={len(mat_result['body'])}")

        # 4. Try search via material_list
        print("\n[3] Try search via material_list...")
        search_result = await page.evaluate("""
            async (params) => {
                try {
                    const url = `/pc/selection/common/material_list?ewid=${params.ewid}&keyword=T%E6%81%A4&channel_id=200&material_type=promotion_id&recall_type=Search&page=1&size=20`;
                    const resp = await fetch(url, {credentials: 'include', headers: {'Accept': 'application/json'}});
                    const text = await resp.text();
                    return {status: resp.status, body: text};
                } catch(e) {
                    return {status: 0, body: e.message};
                }
            }
        """, {"ewid": ewid})
        if search_result["status"] == 200:
            try:
                search_data = json.loads(search_result["body"])
                promos = search_data.get("data", {}).get("promotions", [])
                has_more = search_data.get("data", {}).get("has_more")
                print(f"  Search 'T恤': promotions={len(promos)} has_more={has_more}")
                if promos:
                    pm = promos[0]
                    print(f"    first promo keys: {list(pm.keys())[:15]}")
                    print(f"    first promo: {json.dumps(pm, ensure_ascii=False)[:400]}")
                output_file3 = OUTPUT_DIR / "buyin_search_result.json"
                with open(output_file3, "w", encoding="utf-8") as f:
                    json.dump(search_data, f, ensure_ascii=False, indent=2)
                print(f"  Saved to: {output_file3}")
            except:
                print(f"  Parse error, len={len(search_result['body'])}")

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
