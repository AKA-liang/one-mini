"""
Buyin spider — cookie-based (same pattern as Chanmama).
Subprocess mode: python app/spiders/buyin.py --keyword "xxx" --limit 10

Uses BUYIN_COOKIE from .env → chromium.launch + cookie injection.
No persistent_context needed — works in Docker.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://buyin.jinritemai.com"
PICKING_LIBRARY_URL = f"{BASE_URL}/dashboard/merch-picking-library"
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


def _save_fresh_cookies(cookie_str: str):
    """Update BUYIN_COOKIE in .env with fresh cookies from browser."""
    try:
        if not os.path.exists(ENV_PATH):
            return
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("BUYIN_COOKIE="):
                lines[i] = f"BUYIN_COOKIE={cookie_str}\n"
                updated = True
                break
        if updated:
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines)
            logger.info("Buyin: Saved fresh cookies to .env")
    except Exception:
        pass


def _delete_lock_files():
    for name in [os.path.join(settings.edge_profile_dir, "LOCK"),
                 os.path.join(settings.edge_profile_dir, "SingletonLock")]:
        fp = os.path.join(settings.edge_user_data, name)
        try:
            if os.path.isdir(fp):
                import shutil
                shutil.rmtree(fp, ignore_errors=True)
            elif os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass


_SEARCH_EXTRACT_JS = r"""
() => {
    const results = [];
    const body = document.body.innerText || '';

    const productRegex = /(.+?)\n.*?\n?到手价\s*¥(\d+\.?\d*)\s*\n月销\s*([\d.,]+[万]?)\s*\n佣金\s*\n?(\d+\.?\d*)\s*%\n赚¥(\d+\.?\d*)/g;
    let match;
    while ((match = productRegex.exec(body)) !== null && results.length < 30) {
        results.push({
            name: match[1].trim(), price: match[2], sales: match[3],
            commissionRate: match[4], earn: match[5],
        });
    }

    if (results.length === 0) {
        const lines = body.split('\n');
        let current = {};
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const priceMatch = line.match(/到手价\s*¥(\d+\.?\d*)/);
            if (priceMatch) {
                if (current.price) results.push({...current});
                current = { price: priceMatch[1], sales: '', commissionRate: '', earn: '' };
                const salesMatch = line.match(/月销\s*([\d.,]+[万]?)/);
                if (salesMatch) current.sales = salesMatch[1];
                // Look back for commission + earn + name
                const peek = lines.slice(Math.max(0, i-2), i+2).join('\n');
                const commMatch = peek.match(/(\d+\.?\d*)\s*%/);
                if (commMatch) current.commissionRate = commMatch[1];
                const earnMatch = peek.match(/赚¥(\d+\.?\d*)/);
                if (earnMatch) current.earn = earnMatch[1];
                for (let j = i - 1; j >= Math.max(0, i - 5); j--) {
                    const prev = lines[j].trim();
                    if (prev && prev.length > 4 && !prev.startsWith('¥')
                        && !prev.includes('到手价') && !prev.includes('月销')
                        && !prev.includes('佣金') && !prev.includes('赚¥')
                        && !prev.includes('加选品车')) {
                        current.name = prev;
                        break;
                    }
                }
            }
        }
        if (current.price) results.push({...current});
    }
    return results;
}
"""


def _normalize_product(item: dict[str, Any]) -> dict[str, Any] | None:
    name = str(item.get("name") or "").strip()
    if not name or len(name) < 3:
        return None

    try:
        price = float(str(item.get("price") or "0"))
    except ValueError:
        price = 0
    try:
        commission_rate = float(str(item.get("commissionRate") or "0")) / 100
    except ValueError:
        commission_rate = 0
    try:
        sales_str = str(item.get("sales") or "0")
        sales = float(sales_str.replace("万", "").replace(",", ""))
        sales = sales * 10000 if "万" in sales_str else sales
    except ValueError:
        sales = 0

    return {
        "product_name": name[:200],
        "price": price,
        "commission_rate": commission_rate,
        "sales": int(sales),
        "earn": str(item.get("earn") or ""),
        "source": "buyin",
    }


def search_buyin(keyword: str = "", limit: int = 10) -> list[dict[str, Any]]:
    if not keyword:
        return []

    logger.info(f"Buyin: Searching '{keyword}'")

    extracted_items: list[dict[str, Any]] = []

    try:
        from app.spiders.browser import get_browser

        async def _do_search():
            browser = await get_browser()
            page = await browser.new_page()

            # Navigate to picking library
            await page.goto(PICKING_LIBRARY_URL, wait_until="networkidle", timeout=60000)

            # Wait for SPA to render the search input
            await page.wait_for_selector('.auxo-input, input[type="search"]', timeout=20000)
            await page.wait_for_timeout(3000)

            # Find and use search input
            search_input = await page.query_selector('.auxo-input, input[type="search"]')
            if search_input:
                await search_input.click()
                await page.wait_for_timeout(500)
                await search_input.type(keyword, delay=50)
                await page.wait_for_timeout(500)
                await search_input.press("Enter")

                # Wait for search results to load
                try:
                    await page.wait_for_selector('text=/到手价/', timeout=25000)
                except Exception:
                    pass
                await page.wait_for_timeout(5000)

                # Scroll to load more
                for _ in range(3):
                    await page.mouse.wheel(0, 800)
                    await page.wait_for_timeout(1000)
                await page.wait_for_timeout(3000)

                logger.info(f"Buyin: Searched for '{keyword}'")
            else:
                logger.warning("Buyin: Search input not found")

            # Error detection
            body_text = await page.evaluate("document.body.innerText || ''")
            error_patterns = [
                ("网络不稳定", "Network unstable"),
                ("请稍后再试", "Please retry later"),
                ("登录", "Login required"),
                ("验证", "Captcha/verification detected"),
                ("请求失败", "Request failed"),
                ("系统错误", "System error"),
            ]
            for pat, msg in error_patterns:
                if pat in body_text:
                    logger.warning(f"Buyin: Browser error — {msg}")
                    print(f"[Buyin] ⚠️ {msg}", file=sys.stderr, flush=True)
                    await page.close()
                    return []

            # Extract product data
            data = await page.evaluate(_SEARCH_EXTRACT_JS)
            await page.close()
            return data

        from app.spiders.browser import get_browser
        import asyncio as _asyncio

        async def _search():
            browser = await get_browser()
            page = await browser.new_page()

            await page.goto(PICKING_LIBRARY_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector('.auxo-input, input[type="search"]', timeout=20000)
            await page.wait_for_timeout(3000)

            search_input = await page.query_selector('.auxo-input, input[type="search"]')
            if search_input:
                await search_input.click()
                await page.wait_for_timeout(500)
                await search_input.type(keyword, delay=50)
                await page.wait_for_timeout(500)
                await search_input.press("Enter")
                try:
                    await page.wait_for_selector('text=/到手价/', timeout=25000)
                except Exception:
                    pass
                await page.wait_for_timeout(5000)
                for _ in range(3):
                    await page.mouse.wheel(0, 800)
                    await page.wait_for_timeout(1000)
                await page.wait_for_timeout(3000)
                logger.info(f"Buyin: Searched for '{keyword}'")
            else:
                logger.warning("Buyin: Search input not found")

            body_text = await page.evaluate("document.body.innerText || ''")
            for pat, msg in [("网络不稳定", "Network"), ("请稍后再试", "Retry"),
                             ("登录", "Login"), ("验证", "Capcha"), ("系统错误", "Error")]:
                if pat in body_text:
                    logger.warning(f"Buyin: Error — {msg}")
                    await page.close()
                    return []

            data = await page.evaluate(_SEARCH_EXTRACT_JS)
            await page.close()
            return data

        extracted_items = _asyncio.run(_search())

    except Exception as e:
        logger.warning(f"Buyin: CDP search failed: {e} — falling back to persistent_context")
        extracted_items = _search_via_persistent_context(keyword)

    if not extracted_items:
        return []

    products = []
    seen: set[str] = set()
    # Extract core search term for relevance check
    search_terms = re.split(r"[\s\-/]", keyword) if keyword else []
    search_terms = [t for t in search_terms if len(t) >= 2]
    for item in extracted_items:
        if isinstance(item, dict):
            normalized = _normalize_product(item)
            name = normalized.get("product_name", "") if normalized else ""
            if not name or name in seen:
                continue
            # Relevance check: at least one search term should appear in result
            if search_terms and not any(t in name for t in search_terms):
                continue
            seen.add(name)
            products.append(normalized)

    logger.info(f"Buyin: Found {len(products)} products (validated against keyword)")
    if not products and extracted_items:
        logger.warning("Buyin: Search returned results but none matched the keyword — possible page error")
    return products[:limit]


def _search_via_persistent_context(keyword: str) -> list[dict[str, Any]]:
    """Fallback: use persistent_context if CDP is unavailable."""
    from playwright.sync_api import sync_playwright
    from app.config import settings

    extracted_items: list[dict[str, Any]] = []

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=settings.edge_user_data,
                headless=False, channel="msedge",
                args=["--disable-infobars", f"--profile-directory={settings.edge_profile_dir}"],
                viewport={"width": 1920, "height": 1080}, locale="zh-CN",
                ignore_default_args=["--enable-automation", "--no-sandbox"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                window.chrome = { runtime: {} };
            """)
            page.goto(PICKING_LIBRARY_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)

            search_input = page.query_selector('.auxo-input, input[type="search"]')
            if search_input:
                search_input.click()
                page.wait_for_timeout(300)
                search_input.type(keyword, delay=50)
                page.wait_for_timeout(800)
                search_input.press("Enter")
                page.wait_for_timeout(12000)

            for _ in range(3):
                page.mouse.wheel(0, 800)
                page.wait_for_timeout(1000)
            page.wait_for_timeout(3000)
            extracted_items = page.evaluate(_SEARCH_EXTRACT_JS)
            context.close()
    except Exception as e:
        logger.warning(f"Buyin: persistent_context fallback also failed: {e}")

    return extracted_items if isinstance(extracted_items, list) else []


if __name__ == "__main__":
    import os as _os, sys as _sys
    _os.chdir(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    _sys.path.insert(0, _os.getcwd())

    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", default="")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    result = search_buyin(keyword=args.keyword, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False))
