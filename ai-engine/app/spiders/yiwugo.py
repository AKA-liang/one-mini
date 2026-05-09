from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any
from urllib.parse import quote

from playwright.async_api import async_playwright
from app.spiders.cookie_manager import get_yiwugo_cookie_string, has_yiwugo_cookies

logger = logging.getLogger(__name__)

YIWUGO_BASE_URL = "https://www.yiwugo.com"

_last_request_time = 0.0
_MIN_INTERVAL = 3.0
_MAX_INTERVAL = 7.0


def _throttle():
    global _last_request_time
    now = asyncio.get_event_loop().time()
    elapsed = now - _last_request_time
    wait_time = max(0, random.uniform(_MIN_INTERVAL, _MAX_INTERVAL) - elapsed)
    if wait_time > 0:
        asyncio.sleep(wait_time)
    _last_request_time = asyncio.get_event_loop().time()


async def _fetch_with_playwright(url: str) -> tuple[str, str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context()
        if has_yiwugo_cookies():
            cookie_str = get_yiwugo_cookie_string()
            cookies = []
            for part in cookie_str.split("; "):
                if "=" in part:
                    name, value = part.split("=", 1)
                    cookies.append({"name": name, "value": value, "domain": ".yiwugo.com", "path": "/"})
            await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)

        html = await page.content()
        current_url = page.url

        await browser.close()
        return current_url, html


def search_products(
    keyword: str,
    page: int = 1,
    limit: int = 20,
) -> list[dict[str, Any]]:
    try:
        gbk_keyword = quote(keyword.encode("gbk", errors="replace"))
    except Exception:
        gbk_keyword = quote(keyword)
    url = f"{YIWUGO_BASE_URL}/search?q={gbk_keyword}"
    if page > 1:
        url += f"&page={page}"
    logger.info(f"Yiwugo: Searching for '{keyword}' at {url}")

    try:
        current_url, html = asyncio.run(_fetch_with_playwright(url))
        logger.info(f"Yiwugo: Final URL: {current_url}")

        if "login" in current_url.lower() or "captcha" in current_url.lower():
            logger.warning("Yiwugo: Blocked or redirected to login")
            return []

        products = _parse_from_html(html, keyword)
        if products:
            logger.info(f"Yiwugo: Parsed {len(products)} products")
            return products[:limit]
        else:
            logger.info("Yiwugo: No products found")
            return []
    except Exception as e:
        logger.warning(f"Yiwugo: Playwright failed: {e}")
        return []


def _parse_from_html(html: str, keyword: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    products_section = re.search(
        r'class="products-list"(.*?)(?:class="(?:pagination|footer|page|ant-pagination))',
        html, re.DOTALL,
    )
    if not products_section:
        products_section = re.search(r'class="products-list"(.*)', html, re.DOTALL)
    if not products_section:
        return products

    section = products_section.group(1)
    parts = section.split('class="product-name"')

    for part in parts[1:]:
        try:
            product = _parse_product_block(part, keyword)
            if product and product.get("product_name"):
                products.append(product)
        except Exception:
            continue

    return products[:60]


def _parse_product_block(block: str, keyword: str) -> dict[str, Any]:
    product: dict[str, Any] = {"source": "yiwugo"}

    # Extract product name: <span>text with <font color="red">highlight</font>text</span>
    name_span = re.search(r'<span[^>]*>(.*?)</span>', block, re.DOTALL)
    if name_span:
        raw_name = name_span.group(1)
        name = re.sub(r'<[^>]+>', '', raw_name)
        name = re.sub(r'\s+', ' ', name).strip()
        product["product_name"] = name[:200]
    else:
        return {}

    # Extract price: class="start-price" contains <span class="f18">110</span> <span class="f12">.00</span>
    price_section = re.search(r'class="price"(.*?)(?=class="(?:product-name|shop|price"|tag))', block, re.DOTALL)
    if not price_section:
        price_section = re.search(r'class="price"(.*?)(?=<div[^>]*class="[^"]*shop)', block, re.DOTALL)
    if not price_section:
        price_section = re.search(r'class="price"(.*?)</div>', block, re.DOTALL)

    if price_section:
        price_html = price_section.group(1)
        price_parts = re.findall(r'class="f18"[^>]*>(\d+)', price_html)
        decimal_parts = re.findall(r'class="f12"[^>]*>(\.\d+)', price_html)

        if price_parts:
            prices = []
            i = 0
            while i < len(price_parts):
                whole = price_parts[i]
                decimal = decimal_parts[i] if i < len(decimal_parts) else ""
                try:
                    prices.append(float(whole + decimal))
                except ValueError:
                    pass
                i += 1
                # Skip the second number in a range (it's the max price)
                if i < len(price_parts) and "~" in price_html[:price_html.index(price_parts[i]) if price_parts[i] in price_html else len(price_html)]:
                    whole2 = price_parts[i]
                    decimal2 = decimal_parts[i] if i < len(decimal_parts) else ""
                    try:
                        prices.append(float(whole2 + decimal2))
                    except ValueError:
                        pass
                    i += 1

            # Better approach: just collect all f18 numbers
            prices = []
            f18_matches = re.finditer(r'class="f18"[^>]*>(\d+)', price_html)
            f12_matches = list(re.finditer(r'class="f12"[^>]*>(\.\d+)', price_html))

            f18_list = list(f18_matches)
            for idx, m in enumerate(f18_list):
                whole = m.group(1)
                decimal = ""
                if idx < len(f12_matches):
                    decimal = f12_matches[idx].group(1)
                try:
                    prices.append(float(whole + decimal))
                except ValueError:
                    pass

            if len(prices) >= 2:
                product["price_min"] = min(prices)
                product["price_max"] = max(prices)
            elif len(prices) == 1:
                product["price_min"] = prices[0]
                product["price_max"] = prices[0]

    # Extract shop name
    shop_match = re.search(r'class="[^"]*shop[^"]*name[^"]*"[^>]*>(.*?)<', block, re.DOTALL)
    if shop_match:
        product["shop_name"] = re.sub(r'<[^>]+>', '', shop_match.group(1)).strip()

    # Extract product URL
    link_match = re.search(r'href="(/hu/[^"]+)"', block)
    if link_match:
        product["product_url"] = f"{YIWUGO_BASE_URL}{link_match.group(1)}"

    # Extract MOQ
    moq_match = re.search(r'(\d+)\s*[件个只套起箱批]', block)
    if moq_match:
        product["moq"] = int(moq_match.group(1))

    return product


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()
