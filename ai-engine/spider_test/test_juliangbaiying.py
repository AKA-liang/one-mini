import asyncio
import json
import sys
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("pip install playwright && playwright install")
    sys.exit(1)

EDGE_USER_DATA = r"C:\Users\13265\AppData\Local\Microsoft\Edge\User Data"
EDGE_PROFILE = "Profile 1"

BUYIN_URLS = {
    "login": "https://buyin.jinritemai.com/mpa/account/login?type=24",
    "dashboard": "https://buyin.jinritemai.com/dashboard",
    "selection": "https://buyin.jinritemai.com/dashboard/service/selection",
    "selection_square": "https://buyin.jinritemai.com/dashboard/service/selection/square",
}

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def explore_buyin():
    print("=" * 60)
    print("Buyin Exploration - Local Spider Test")
    print("=" * 60)

    api_responses: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        async def handle_response(response):
            url = response.url
            if any(kw in url for kw in ["api", "selection", "product", "goods", "item", "alliance", "search", "login", "getUser"]):
                if any(skip in url for kw in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", "monitor", "mcs.zijieapi", "vcs.zijieapi", "mon.zijieapi"] for skip in [kw]):
                    return
                try:
                    body = await response.text()
                    if body and len(body) > 30:
                        api_responses.append({
                            "url": url,
                            "status": response.status,
                            "body_preview": body[:3000],
                        })
                        print(f"  [API] {response.status} {url[:120]}")
                        print(f"        body({len(body)}): {body[:200]}...")
                except Exception:
                    pass

        page.on("response", handle_response)

        # Step 1: Check login status
        print("\n[Step 1] Check login status...")
        try:
            await page.goto("https://buyin.jinritemai.com/dashboard", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            title = await page.title()
            url = page.url
            print(f"  title: {title}")
            print(f"  url: {url}")

            if "login" in url.lower() or "douyinec" in url.lower():
                print("  [!] Not logged in or redirected. Trying login page...")
                await page.goto(BUYIN_URLS["login"], wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                title = await page.title()
                url = page.url
                print(f"  login title: {title}")
                print(f"  login url: {url}")

                screenshot_file = OUTPUT_DIR / "buyin_login.png"
                await page.screenshot(path=str(screenshot_file))
                print(f"  Screenshot saved: {screenshot_file}")
                print("\n  >>> Please log in manually in the Edge browser, then re-run this script.")
                await browser.close()
                return

            print("  [OK] Already logged in")
        except Exception as e:
            print(f"  [ERROR] {e}")
            await browser.close()
            return

        # Step 2: Explore selection pages
        print("\n[Step 2] Explore selection pages...")
        for name, url in BUYIN_URLS.items():
            if name in ("login", "dashboard"):
                continue
            print(f"\n  Trying: {name} -> {url}")
            try:
                api_responses.clear()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(5000)

                print(f"  Page title: {await page.title()}")
                print(f"  Current URL: {page.url}")
                print(f"  Captured APIs: {len(api_responses)}")

                if api_responses:
                    output_file = OUTPUT_DIR / f"buyin_{name}_api.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(api_responses, f, ensure_ascii=False, indent=2)
                    print(f"  Saved API responses to: {output_file}")

                    for resp in api_responses:
                        try:
                            data = json.loads(resp["body_preview"])
                            if isinstance(data, dict):
                                keys = list(data.keys())[:15]
                                print(f"  Fields: {keys}")
                                if "data" in data and isinstance(data["data"], dict):
                                    print(f"  data fields: {list(data['data'].keys())[:15]}")
                        except (json.JSONDecodeError, KeyError):
                            pass
            except Exception as e:
                print(f"  [ERROR] {e}")

        # Step 3: Screenshot and HTML
        screenshot_file = OUTPUT_DIR / "buyin_selection.png"
        await page.screenshot(path=str(screenshot_file), full_page=False)
        print(f"\nScreenshot saved: {screenshot_file}")

        html_content = await page.content()
        html_file = OUTPUT_DIR / "buyin_selection.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML saved: {html_file}")

        await browser.close()

    print(f"\nTotal APIs captured: {len(api_responses)}")
    print(f"Output dir: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(explore_buyin())
