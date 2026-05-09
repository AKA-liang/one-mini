import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

BUYIN_URLS = [
    ("/merch-picking-hall/center", "picking_hall_center"),
    ("/merch-picking-hall", "picking_hall"),
    ("/merch-picking-library", "picking_library"),
    ("/exclusive-selection-square/picking", "exclusive_picking"),
    ("/exclusive-selection-square/rank", "exclusive_rank"),
    ("/exclusive-selection-square/home", "exclusive_home"),
    ("/merch-picking-utils/hot-spot", "hot_spot"),
    ("/merch-picking-hall/rank", "daren_rank"),
]


async def main():
    print("=" * 60)
    print("Buyin Product API Capture - Correct URLs")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]

        for path, name in BUYIN_URLS:
            all_responses: list[dict] = []

            page = await context.new_page()

            async def on_response(response):
                url = response.url
                if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico", ".gif", ".avif", ".webp", ".woff2", ".ttf", ".map"]):
                    return
                if response.status != 200:
                    return
                try:
                    body = await response.text()
                    if not body or len(body) < 100:
                        return
                    try:
                        data = json.loads(body)
                        all_responses.append({"url": url, "status": response.status, "body": body[:10000]})
                    except (json.JSONDecodeError, ValueError):
                        pass
                except Exception:
                    pass

            page.on("response", on_response)

            full_url = f"https://buyin.jinritemai.com/dashboard{path}"
            print(f"\n[Navigate] {name}: {full_url}")

            try:
                await page.goto(full_url, timeout=30000)
                await page.wait_for_timeout(12000)

                # Scroll
                for i in range(3):
                    await page.evaluate("window.scrollBy(0, 800)")
                    await page.wait_for_timeout(1500)
                await page.wait_for_timeout(3000)

                print(f"  Page title: {await page.title()}")
                print(f"  Final URL: {page.url}")
                print(f"  Captured: {len(all_responses)} JSON responses")

                # Check page content
                body_text = await page.evaluate("() => document.body.innerText.substring(0, 300)")
                has_content = len(body_text) > 200
                print(f"  Page text length: {len(body_text)} (has_content={has_content})")

                # Find product data
                for resp in all_responses:
                    body = resp["body"]
                    try:
                        data = json.loads(body)
                        d = data.get("data")
                        if isinstance(d, dict) and any(k in str(d.keys()).lower() for k in ["product", "goods", "item", "list", "rank", "commission"]):
                            keys_str = str(list(d.keys())[:15])
                            print(f"  [PRODUCT DATA] {resp['url'][:120]}")
                            print(f"    data.keys: {keys_str}")
                            print(f"    body preview: {body[:300]}")
                    except:
                        pass

                # Save
                if all_responses:
                    output_file = OUTPUT_DIR / f"buyin_{name}.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(all_responses, f, ensure_ascii=False, indent=2)
                    print(f"  Saved to: {output_file}")

            except Exception as e:
                print(f"  ERROR: {e}")

            await page.close()

        await browser.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
