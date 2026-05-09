import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    print("=" * 60)
    print("Buyin API Capture v3 - Direct navigate + listener")
    print("=" * 60)

    all_responses: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]

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
                    json.loads(body)
                    all_responses.append({"url": url, "status": response.status, "body": body[:10000]})
                except (json.JSONDecodeError, ValueError):
                    pass
            except Exception:
                pass

        page.on("response", on_response)

        print("\n[Navigate] to selection square...")
        await page.goto("https://buyin.jinritemai.com/dashboard/service/selection/square", timeout=60000)
        print("  Page loaded. Waiting 20s for full SPA render...")
        await page.wait_for_timeout(20000)

        # Scroll
        print("[Scroll] triggering lazy load...")
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(2000)

        await page.wait_for_timeout(5000)

        # Check page content
        body_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
        print(f"\n[Page content] ({len(body_text)} chars):")
        print(f"  {body_text[:300]}")

        # Check URL
        print(f"\n[Page URL] {page.url}")

        print(f"\n[Captured] {len(all_responses)} JSON API responses")

        # Display unique URLs
        seen = set()
        print("\n=== All Unique API URLs ===")
        for resp in all_responses:
            base = resp["url"].split("?")[0]
            if base not in seen:
                seen.add(base)
                print(f"  {len(resp['body']):>6}  {base}")

        # Find product data
        print("\n=== Product-like APIs ===")
        for resp in all_responses:
            body = resp["body"].lower()
            if any(kw in body for kw in ["commission_rate", "product_id", "goods_id", "price_info", "sales_info"]):
                print(f"  {resp['url'][:150]}")
                print(f"  Body: {resp['body'][:500]}")

        # Save
        output_file = OUTPUT_DIR / "buyin_v3_captured.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_responses, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {output_file}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
