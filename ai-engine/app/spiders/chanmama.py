"""
Chanmama spider — SPU rank data via API interception.

Provides 26 structured fields per product including:
  title, brand, sales_volume, sales_amount, live/video split,
  creator count (competition), shop count (supply), sales indices.

Plan A: cookie injection → intercept /v1/spu/search API → parse 26 fields → up to 100 items
Plan B: persistent_context fallback (when cookie fails)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from app.spiders.cookie_manager import get_chanmama_cookie_string, has_chanmama_cookies
from app.config import settings

logger = logging.getLogger(__name__)

CHANMAMA_BASE_URL = "https://www.chanmama.com"
SPU_API_URL = "https://api-service.chanmama.com/v1/spu/search"

_MAX_ITEMS = 100
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class SpiderAuthError(Exception):
    """Raised when spider detects authentication failure (401/403/login redirect)."""
    pass


def _save_chanmama_cookies(cookie_str: str):
    """Update CHANMAMA_COOKIE in .env with fresh cookies from browser."""
    try:
        if not os.path.exists(ENV_PATH):
            return
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("CHANMAMA_COOKIE="):
                lines[i] = f"CHANMAMA_COOKIE={cookie_str}\n"
                updated = True
                break
        if not updated:
            lines.append(f"\nCHANMAMA_COOKIE={cookie_str}\n")
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        logger.info("Chanmama: Saved fresh cookies to .env")
    except Exception as e:
        logger.warning(f"Chanmama: Failed to save cookies to .env: {e}")


def _normalize_spu_item(item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title") or "")[:200]
    brand = str(item.get("brand_name") or item.get("brand") or "")
    spu_id = str(item.get("spu_id") or "")

    def _num(v) -> float | None:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "title": title,
        "brand": brand,
        "spu_id": spu_id,
        "image": str(item.get("img") or item.get("image") or ""),
        # Sales ranges (text)
        "sales_volume_text": str(item.get("duration_volume_text") or ""),
        "sales_amount_text": str(item.get("duration_amount_text") or ""),
        "live_volume_text": str(item.get("duration_live_volume_text") or ""),
        "live_amount_text": str(item.get("duration_live_amount_text") or ""),
        "video_volume_text": str(item.get("duration_aweme_volume_text") or ""),
        "video_amount_text": str(item.get("duration_aweme_amount_text") or ""),
        # Sales indices (numeric) — demand intensity
        "sales_volume_index": _num(item.get("duration_volume_text_cmm_ind")),
        "sales_amount_index": _num(item.get("duration_amount_text_cmm_ind")),
        "live_volume_index": _num(item.get("duration_live_volume_text_cmm_ind")),
        "live_amount_index": _num(item.get("duration_live_amount_text_cmm_ind")),
        "video_volume_index": _num(item.get("duration_aweme_volume_text_cmm_ind")),
        "video_amount_index": _num(item.get("duration_aweme_amount_text_cmm_ind")),
        "other_volume_index": _num(item.get("duration_other_volume_text_cmm_ind")),
        "other_amount_index": _num(item.get("duration_other_amount_text_cmm_ind")),
        # Supply / competition indicators
        "product_count": item.get("duration_product_count"),
        "creator_count": item.get("duration_author_count"),
        "shop_count": item.get("duration_shop_count"),
        "live_count": item.get("duration_live_count"),
        "aweme_count": item.get("duration_aweme_count"),
        # Price (hidden by Chanmama)
        "price_hidden": True,
        "source": "chanmama",
    }


async def _build_cookie_context(browser):
    ctx = await browser.new_context(locale="zh-CN")
    if has_chanmama_cookies():
        cs = get_chanmama_cookie_string()
        cookies = []
        for part in cs.split("; "):
            if "=" in part:
                n, v = part.split("=", 1)
                cookies.append({"name": n, "value": v, "domain": ".chanmama.com", "path": "/"})
        await ctx.add_cookies(cookies)
    return ctx


async def _fetch_spu_page(keyword: str, page_num: int = 1, size: int = 50) -> list[dict[str, Any]]:
    """Navigate to SPUrank page and intercept the search API response. Returns parsed items."""
    from playwright.async_api import async_playwright

    captured_data: list[dict[str, Any]] = []
    error_flag: list[str] = []

    async def _on_response(response):
        try:
            url = response.url
            if response.status in (401, 403) and "chanmama.com" in url:
                error_flag.append(f"Auth failure HTTP {response.status} on {url}")
            if response.status == 200 and "/v1/spu/search" in url:
                body = await response.json()
                data = body.get("data", {}).get("list", [])
                if isinstance(data, list):
                    captured_data.extend(data)
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        ctx = await _build_cookie_context(browser)
        page = await ctx.new_page()
        page.on("response", _on_response)

        url = f"{CHANMAMA_BASE_URL}/SPUrank/?keyword={keyword}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            await page.goto(url, wait_until="load", timeout=30000)

        await asyncio.sleep(5)

        cur_url = page.url
        if "/register" in cur_url or "/login" in cur_url:
            error_flag.append(f"redirected to {cur_url}")
            await browser.close()
            return []

        # Save fresh cookies from successful session
        if captured_data:
            try:
                cookies = await ctx.cookies()
                cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('name') and c.get('value'))
                if cookie_str:
                    _save_chanmama_cookies(cookie_str)
            except Exception:
                pass

        await browser.close()

    if error_flag:
        msg = error_flag[0]
        logger.warning(f"Chanmama API fetch aborted: {msg}")
        raise SpiderAuthError(msg)

    return captured_data


def search_hot_products(
    keyword: str = "",
    category: str = "",
    date_type: str = "day",
    page: int = 1,
    limit: int = 20,
) -> list[dict[str, Any]]:
    limit = min(limit, _MAX_ITEMS)
    logger.info(f"Chanmama: API mode — searching '{keyword}' (limit={limit})")

    try:
        # Page 1: up to 50 items
        raw_items = asyncio.run(_fetch_spu_page(keyword, page_num=1, size=50))
        if not raw_items:
            logger.info("Chanmama: No items from API — page may need JS re-render, falling back to Plan B")
            return []

        # Page 2: if page 1 returned 50 and we want more
        if len(raw_items) >= 50 and limit > 50:
            page2_raw = asyncio.run(_fetch_spu_page(keyword, page_num=2, size=50))
            if page2_raw:
                raw_items.extend(page2_raw)

        products = []
        seen_names: set[str] = set()
        for item in raw_items[:limit]:
            normalized = _normalize_spu_item(item)
            name = normalized.get("title", "")
            if not name:
                continue
            simple_name = re.sub(r"[\s\-_]", "", name)[:30].lower()
            if simple_name in seen_names:
                continue
            seen_names.add(simple_name)
            products.append(normalized)

        logger.info(f"Chanmama: API returned {len(products)} products (from {len(raw_items)} raw)")
        return products[:limit]

    except Exception as e:
        logger.warning(f"Chanmama: API mode failed: {e}")
        return []


def _search_via_persistent_context(keyword: str) -> list[dict[str, Any]]:
    """Fallback: persistent_context if CDP unavailable."""
    from playwright.sync_api import sync_playwright
    from app.config import settings

    captured_items: list[dict[str, Any]] = []
    auth_errors: list[str] = []
    url = f"{CHANMAMA_BASE_URL}/SPUrank/?keyword={keyword}"

    def _handle_response(response):
        try:
            if response.status in (401, 403) and "chanmama.com" in response.url:
                auth_errors.append(f"Auth failure HTTP {response.status} on {response.url}")
            if response.status == 200 and "/v1/spu/search" in response.url:
                body = response.json()
                data = body.get("data", {}).get("list", [])
                if isinstance(data, list):
                    captured_items.extend(data)
        except Exception:
            pass

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=settings.edge_user_data, headless=False, channel="msedge",
                args=["--disable-infobars", f"--profile-directory={settings.edge_profile_dir}"],
                viewport={"width": 1920, "height": 1080}, locale="zh-CN",
                ignore_default_args=["--enable-automation"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                window.chrome = { runtime: {} };
                window.navigator.chrome = { runtime: {} };
            """)
            page.on("response", _handle_response)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            if captured_items:
                try:
                    cookies = context.cookies()
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get('name') and c.get('value'))
                    if cookie_str:
                        _save_chanmama_cookies(cookie_str)
                except Exception:
                    pass
            context.close()
    except Exception:
        pass

    if auth_errors:
        raise SpiderAuthError(auth_errors[0])

    return captured_items


def search_hot_products_persistent(
    keyword: str = "",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Primary: persistent_context with real Edge profile + API interception.
    """
    limit = min(limit, _MAX_ITEMS)
    captured_items = _search_via_persistent_context(keyword)

    products = []
    seen: set[str] = set()
    for item in captured_items[:limit]:
        normalized = _normalize_spu_item(item)
        name = normalized.get("title", "")
        if not name:
            continue
        simple = re.sub(r"[\s\-_]", "", name)[:30].lower()
        if simple in seen:
            continue
        seen.add(simple)
        products.append(normalized)

    logger.info(f"Chanmama(Plan B): {len(products)} products")
    return products[:limit]


def search_trending_keywords() -> list[str]:
    defaults = [
        "美妆护肤", "家居日用", "食品饮料", "服饰穿搭",
        "母婴亲子", "数码家电", "运动户外", "珠宝配饰",
    ]
    return defaults
