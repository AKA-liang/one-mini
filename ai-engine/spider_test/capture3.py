"""promotionRank: type keyword → capture rankList API"""
import sys, os, asyncio, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from app.spiders.cookie_manager import get_chanmama_cookie_string, has_chanmama_cookies


async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        ctx = await browser.new_context(locale="zh-CN")
        if has_chanmama_cookies():
            cs = get_chanmama_cookie_string()
            cookies = []
            for part in cs.split("; "):
                if "=" in part:
                    n, v = part.split("=", 1)
                    cookies.append({"name": n, "value": v, "domain": ".chanmama.com", "path": "/"})
            await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        rank_list_data = None

        async def on_response(response):
            nonlocal rank_list_data
            try:
                url = response.url
                if response.status == 200 and "api-service.chanmama.com/v1/product/new/rankList" in url:
                    if rank_list_data is None:
                        rank_list_data = await response.json()
            except:
                pass

        page.on("response", on_response)

        print("Navigating to promotionRank...")
        await page.goto("https://www.chanmama.com/promotionRank/tikGoodsSale/",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        # Find and type in search input
        print("Looking for search input...")
        # The search input on this page has specific placeholders
        inputs = await page.evaluate("""
        () => {
            const all = document.querySelectorAll('input');
            return Array.from(all).map(i => ({
                type: i.type,
                placeholder: i.getAttribute('placeholder') || '',
                class: (i.className || '').substring(0, 80),
            }));
        }
        """)
        print(f"Found {len(inputs)} inputs:")
        for i, inp in enumerate(inputs):
            if inp["placeholder"] or inp["type"] == "text":
                print(f"  [{i}] type={inp['type']} placeholder='{inp['placeholder']}' class={inp['class']}")

        # Try typing
        search_input = await page.query_selector('input[placeholder*="搜索"], input[placeholder*="输入"]')
        if not search_input:
            search_input = await page.query_selector("input[type='text']")
        if not search_input:
            # Directly use evaluate to find and fill
            await page.evaluate("""
            () => {
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {
                    if (inp.type === 'text' || inp.getAttribute('placeholder')) {
                        inp.value = '手机壳';
                        inp.dispatchEvent(new Event('input', {bubbles: true}));
                        inp.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'}));
                        return true;
                    }
                }
                return false;
            }
            """)
            print("Used JS to type 手机壳")
        else:
            await search_input.click()
            await asyncio.sleep(500)
            await search_input.fill("手机壳")
            await asyncio.sleep(500)
            await page.keyboard.press("Enter")
            print(f"Typed 手机壳 in search input")

        await asyncio.sleep(8)

        if rank_list_data:
            print("\n=== RANK LIST DATA ===")
            items = rank_list_data.get("data", {}).get("list", rank_list_data.get("data", []))
            if isinstance(items, list):
                print(f"Total items: {len(items)}")
                if items:
                    first = items[0]
                    print(f"Keys: {list(first.keys())}")
                    print(f"Sample: {json.dumps(first, ensure_ascii=False, indent=2)}")
            else:
                print(f"Full response: {json.dumps(rank_list_data, ensure_ascii=False)[:2000]}")
        else:
            print(f"No rankList API captured. URL: {page.url[:150]}")
            body = await page.evaluate("document.body.innerText.substring(0, 1000)")
            print(f"Body:\n{body}")

        await browser.close()

asyncio.run(explore())
