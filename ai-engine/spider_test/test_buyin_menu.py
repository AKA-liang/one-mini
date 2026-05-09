import asyncio, json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto("https://buyin.jinritemai.com/dashboard", timeout=30000)
        await page.wait_for_timeout(10000)

        result = await page.evaluate("""
            async () => {
                const resp = await fetch('/api/permission/menu', {credentials: 'include'});
                const data = await resp.json();
                return data;
            }
        """)

        menu_list = result.get("data", {}).get("menu_list", [])
        for item in menu_list:
            name = item.get("name", "")
            url = item.get("url", "")
            children = item.get("children", [])
            print(f"{name} -> {url}")
            if children:
                for child in children:
                    cname = child.get("name", "")
                    curl = child.get("url", "")
                    print(f"  {cname} -> {curl}")
                    gc = child.get("children", [])
                    if gc:
                        for g in gc:
                            gn = g.get("name", "")
                            gu = g.get("url", "")
                            print(f"    {gn} -> {gu}")

        await browser.close()

asyncio.run(main())
