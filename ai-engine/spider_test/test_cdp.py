"""CDP test — single event loop"""
import sys, os, json, asyncio
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, '.')

async def test():
    from app.spiders.chanmama import search_hot_products_persistent
    from app.spiders.browser import get_browser

    browser = await get_browser()

    # ---- Chanmama ----
    print("=== Chanmama CDP ===")
    rcm = search_hot_products_persistent('手机壳', limit=3)
    print(f'Results: {len(rcm)}')
    if rcm:
        f = rcm[0]
        print(f"  title: {f.get('title','')[:40]}")
        print(f"  sales_idx: {f.get('sales_volume_index')}")

    # ---- Buyin CDP directly ----
    print("\n=== Buyin CDP ===")
    from app.spiders.buyin import _SEARCH_EXTRACT_JS, _normalize_product
    page = await browser.new_page()
    await page.goto("https://buyin.jinritemai.com/dashboard/merch-picking-library",
                    wait_until="networkidle", timeout=60000)
    await page.wait_for_selector('.auxo-input, input[type="search"]', timeout=20000)
    await page.wait_for_timeout(3000)

    si = await page.query_selector('.auxo-input, input[type="search"]')
    if si:
        await si.click()
        await page.wait_for_timeout(500)
        await si.type("手机壳", delay=50)
        await page.wait_for_timeout(500)
        await si.press("Enter")
        try:
            await page.wait_for_selector('text=/到手价/', timeout=25000)
        except Exception:
            pass
        await page.wait_for_timeout(5000)

    body_text = await page.evaluate("document.body.innerText || ''")
    print(f"  Body has 网络不稳定: {'网络不稳定' in body_text}")
    print(f"  Body has 到手价: {'到手价' in body_text}")
    print(f"  Body first 300: {body_text[:300]}")

    items = await page.evaluate(_SEARCH_EXTRACT_JS)
    results = []
    seen = set()
    for item in items:
        n = _normalize_product(item)
        if n and n.get("product_name") not in seen:
            seen.add(n["product_name"])
            results.append(n)

    print(f"\n  Products: {len(results)}")
    for p in results:
        print(f"    {p.get('product_name','')[:30]} | ¥{p.get('price')} | {p.get('commission_rate')}")
    await page.close()

asyncio.run(test())
