"""Deep dive: get FULL SPU search API response + SPU detail API.
Check for: price, commission, vendor comparison, sales data."""
import sys, os, asyncio, json, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright

CHANMAMA_COOKIE = "frontend_canary1=none; LOGIN-TOKEN-FORSNS=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBJZCI6MTAwMDAsImFwcFZlcnNpb24iOiIiLCJleHBpcmVfdGltZSI6MTc3ODc4NTIwMCwiaWF0IjoxNzc4MjA4Mjc0LCJpZCI6MTU3MzM4OSwia2lkIjoiVVNFUi1BU0NKSE9YNThKWTgtQUE1V01GIiwicmsiOiJQR25EWCIsInVjaWQiOiJiNWQ5ZmQ1YS0zMjIxLTExZjEtYTljZS1mZTJmMTkyOWQ0MDUifQ.jCmMxULeiIvdQXc35_3qN1NKuXjz7c72_DNclmSBwDA; Authorization-By-CAS=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOjEwMDAwLCJleHAiOjE3Nzg3ODUyMDAsImlhdCI6MTc3ODIwODMyMywicmsiOiJyNjlHciIsInVuaXF1ZV9pZCI6IlVTRVItQVNDSkhPWDU4Slk4LUFBNVdNRiJ9.BMwBJ3KmgD28QoeWUMx4-tECVWr_3pgMUiuT2zgKRg0; CMM_A_C_ID=c1384a62-491d-11f1-88e1-926ac12e6d04; CMM_U_C_ID=b5d9fd5a-3221-11f1-a9ce-fe2f1929d405"


async def explore():
    cookies = []
    for part in CHANMAMA_COOKIE.split("; "):
        if "=" in part:
            n, v = part.split("=", 1)
            cookies.append({"name": n, "value": v, "domain": ".chanmama.com", "path": "/"})

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False)
        ctx = await browser.new_context(locale="zh-CN")
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        full_spu_list = None
        spu_detail_data = []

        async def on_response(response):
            nonlocal full_spu_list
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com" in url:
                    ct = response.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    body = await response.json()
                    body_str = json.dumps(body, ensure_ascii=False)

                    # Capture SPU search results
                    if "/v1/spu/search" in url and not full_spu_list:
                        full_spu_list = body
                        return

                    # Capture SPU detail
                    if "/v1/spu/" in url and "/spu/" not in url.split("/")[-1]:
                        spu_detail_data.append({"url": url[:120], "body": body})

                    # Capture any endpoint with "commission" or "达人" or "price"
                    if any(kw in body_str for kw in ["commission", "佣金", "price_range", "达人列表", "kol",
                                                       "sku_price", "sale_price"]):
                        spu_detail_data.append({"url": url[:120], "body": body})
            except:
                pass

        page.on("response", on_response)

        print("=== Step 1: SPU search API ===")
        await page.goto("https://www.chanmama.com/SPUrank/?keyword=美妆护肤", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(10)

        if full_spu_list:
            data = full_spu_list.get("data", {})
            items = data.get("list", [])
            print(f"Total items: {len(items)}")
            print(f"Total count: {data.get('total_count', data.get('total', 'N/A'))}")
            print(f"Data keys: {list(data.keys())}")
            if items:
                first = items[0]
                print(f"\nFirst item keys: {list(first.keys())}")
                print(f"First item JSON:")
                print(json.dumps(first, ensure_ascii=False, indent=2))
        else:
            print("SPU search API not captured!")

        # ═══ Step 2: Click a product to get detail API ═══
        print("\n=== Step 2: Click product for detail ===")
        await page.evaluate("""
        () => {
            const rows = document.querySelectorAll('[class*="row"], [class*="item"], tr');
            for (const r of rows) {
                if (r.textContent && r.textContent.length > 30) {
                    r.click();
                    return true;
                }
            }
            return false;
        }
        """)
        await asyncio.sleep(5)
        print(f"Current URL after click: {page.url[:200]}")

        # ═══ Step 3: Show captured detail endpoints ═══
        print(f"\n=== Step 3: Detail APIs ({len(spu_detail_data)}) ===")
        for d in spu_detail_data[:5]:
            print(f"\nURL: {d['url'][:130]}")
            body_str = json.dumps(d["body"], ensure_ascii=False)
            print(f"Body (first 800): {body_str[:800]}")

        await browser.close()

asyncio.run(explore())
