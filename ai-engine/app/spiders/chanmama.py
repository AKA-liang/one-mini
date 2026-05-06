from __future__ import annotations

import json
import logging
import re
from typing import Any

from scrapling.fetchers import StealthyFetcher, DynamicFetcher

from app.spiders.cookie_manager import get_chanmama_cookies, has_chanmama_cookies

logger = logging.getLogger(__name__)

CHANMAMA_BASE_URL = "https://www.chanmama.com"


def search_hot_products(
    category: str = "",
    date_type: str = "day",
    page: int = 1,
) -> list[dict[str, Any]]:
    strategies = []
    if has_chanmama_cookies():
        strategies.append(_fetch_with_cookies)
    strategies.extend([_fetch_spu_rank, _fetch_with_dynamic])

    for strategy in strategies:
        try:
            result = strategy(category=category, date_type=date_type, page=page)
            if result:
                logger.info(f"Chanmama: {strategy.__name__} returned {len(result)} products")
                return result
        except Exception as e:
            logger.warning(f"Chanmama: {strategy.__name__} failed: {e}")
            continue

    logger.info("Chanmama: All scraping strategies failed, returning empty list")
    return []


def _fetch_with_cookies(category: str = "", date_type: str = "day", page: int = 1) -> list[dict[str, Any]]:
    url = f"{CHANMAMA_BASE_URL}/SPUrank"
    if category:
        url = f"{CHANMAMA_BASE_URL}/SPUrank?category={category}"

    cookies = get_chanmama_cookies()

    page_data = StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=True,
        cookies=cookies,
        timeout=30000,
    )

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "/register" in current_url or "/login" in current_url:
        logger.info("Chanmama: Redirected to login/register page even with cookies")
        return []

    return _parse_product_page(page_data)


def _fetch_spu_rank(category: str = "", date_type: str = "day", page: int = 1) -> list[dict[str, Any]]:
    url = f"{CHANMAMA_BASE_URL}/SPUrank"
    if category:
        url = f"{CHANMAMA_BASE_URL}/SPUrank?category={category}"

    page_data = StealthyFetcher.fetch(
        url, headless=True, network_idle=True, timeout=30000
    )

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "/register" in current_url or "/login" in current_url:
        logger.info("Chanmama: Redirected to login/register page, skipping")
        return []

    return _parse_product_page(page_data)


def _fetch_with_dynamic(category: str = "", date_type: str = "day", page: int = 1) -> list[dict[str, Any]]:
    url = f"{CHANMAMA_BASE_URL}/SPUrank"
    if category:
        url = f"{CHANMAMA_BASE_URL}/SPUrank?category={category}"

    page_data = DynamicFetcher.fetch(
        url, headless=True, network_idle=True, timeout=30000
    )

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "/register" in current_url or "/login" in current_url:
        logger.info("Chanmama: Redirected to login/register page, skipping")
        return []

    return _parse_product_page(page_data)


def _parse_product_page(page_data: Any) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "/register" in current_url or "/login" in current_url:
        return []

    selectors = [
        "tr", ".rank-item", ".product-item", ".sale-item",
        ".goods-item", "[class*='product']", "[class*='rank']",
    ]

    for selector in selectors:
        rows = page_data.css(selector) if hasattr(page_data, "css") else []
        if rows and len(rows) > 2:
            for row in rows[:20]:
                try:
                    product = _extract_product_from_element(row)
                    if product and product.get("title"):
                        products.append(product)
                except Exception:
                    continue
            if products:
                break

    if not products:
        products = _extract_from_page_text(page_data)

    return products


def _extract_product_from_element(element: Any) -> dict[str, Any] | None:
    text = element.text if hasattr(element, "text") else ""
    if not text or len(text.strip()) < 5:
        return None

    links = element.css("a::attr(href)") if hasattr(element, "css") else []
    product_url = ""
    if links:
        product_url = links[0] if isinstance(links, list) else str(links)

    price_match = re.search(r"[¥￥]\s*(\d+\.?\d*)", text)
    price = float(price_match.group(1)) if price_match else None

    return {
        "title": _clean_text(text[:100]),
        "price": price,
        "raw_text": _clean_text(text[:500]),
        "product_url": product_url,
    }


def _extract_from_page_text(page_data: Any) -> list[dict[str, Any]]:
    full_text = ""
    if hasattr(page_data, "css"):
        body_text = page_data.css("body::text").get()
        if body_text:
            full_text = body_text

    if not full_text:
        return []

    products: list[dict[str, Any]] = []
    price_matches = re.finditer(r"[¥￥]\s*(\d+\.?\d*)", full_text)
    for idx, match in enumerate(price_matches):
        if idx >= 20:
            break
        start = max(0, match.start() - 50)
        end = min(len(full_text), match.end() + 50)
        context = _clean_text(full_text[start:end])
        products.append({
            "title": context[:80],
            "price": float(match.group(1)),
            "raw_text": context,
            "product_url": "",
        })

    return products


def search_product_detail(product_url: str) -> dict[str, Any] | None:
    if not product_url.startswith("http"):
        product_url = f"{CHANMAMA_BASE_URL}{product_url}"

    try:
        page_data = StealthyFetcher.fetch(
            product_url, headless=True, network_idle=True, timeout=30000
        )
        return _parse_detail_page(page_data)
    except Exception:
        return None


def _parse_detail_page(page_data: Any) -> dict[str, Any] | None:
    detail: dict[str, Any] = {}

    if hasattr(page_data, "css"):
        title_el = page_data.css("h1::text").get()
        if title_el:
            detail["title"] = title_el.strip()

        price_els = page_data.css(".price::text").getall()
        if price_els:
            detail["prices"] = [p.strip() for p in price_els if p.strip()]

    return detail if detail else None


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_trending_keywords() -> list[str]:
    defaults = [
        "美妆护肤", "家居日用", "食品饮料", "服饰穿搭",
        "母婴亲子", "数码家电", "运动户外", "珠宝配饰",
    ]
    return defaults