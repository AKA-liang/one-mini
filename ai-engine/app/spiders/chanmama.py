from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from typing import Any

from playwright.async_api import async_playwright
from app.spiders.cookie_manager import get_chanmama_cookie_string, has_chanmama_cookies

logger = logging.getLogger(__name__)

CHANMAMA_BASE_URL = "https://www.chanmama.com"

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


async def _fetch_with_playwright(url: str) -> tuple[str, Any]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        
        # Load cookies from env if available
        context = await browser.new_context()
        if has_chanmama_cookies():
            cookie_str = get_chanmama_cookie_string()
            cookies = []
            for part in cookie_str.split("; "):
                if "=" in part:
                    name, value = part.split("=", 1)
                    cookies.append({
                        "name": name,
                        "value": value,
                        "domain": ".chanmama.com",
                        "path": "/"
                    })
            await context.add_cookies(cookies)
        
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        html = await page.content()
        current_url = page.url
        
        await browser.close()
        return current_url, html


def search_hot_products(
    keyword: str = "",
    category: str = "",
    date_type: str = "day",
    page: int = 1,
    limit: int = 20
) -> list[dict[str, Any]]:
    # Determine URL: if keyword provided use search, else use SPU rank
    if keyword:
        url = f"{CHANMAMA_BASE_URL}/search?q={keyword}"
        logger.info(f"Chanmama: Searching for keyword '{keyword}' at {url}")
    else:
        url = f"{CHANMAMA_BASE_URL}/SPUrank"
        if category:
            url = f"{CHANMAMA_BASE_URL}/SPUrank?category={category}"
        logger.info(f"Chanmama: Fetching SPU rank page {url}")
    
    try:
        current_url, html = asyncio.run(_fetch_with_playwright(url))
        logger.info(f"Chanmama: Final URL after redirect: {current_url}")
        
        if "/register" in current_url or "/login" in current_url:
            logger.warning("Chanmama: Redirected to login/register, cookie may be expired!")
            return []
        
        # Try to extract products from HTML
        products = _parse_from_html(html)
        if products:
            logger.info(f"Chanmama: Parsed {len(products)} products from HTML")
            return products[:limit]
        else:
            logger.info("Chanmama: No products found via HTML parse")
            return []
    except Exception as e:
        logger.warning(f"Chanmama: Playwright fetch failed: {e}")
        return []


def _parse_from_html(html: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    
    # Try to find common product elements
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    if len(rows) < 5:
        rows = re.findall(r'<div[^>]*class="[^"]*rank[^"]*item[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    if len(rows) < 5:
        rows = re.findall(r'<div[^>]*class="[^"]*product[^"]*item[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
    
    if len(rows) > 5:
        for row in rows[:50]:
            try:
                title_match = re.search(r'>([^<>]{5,100})<', row)
                price_match = re.search(r'[¥￥]\s*([0-9.,]+)', row)
                
                if title_match:
                    title = _clean_text(title_match.group(1))
                    if title:
                        product = {"title": title, "raw_text": _clean_text(row[:500])}
                        if price_match:
                            product["price"] = float(price_match.group(1).replace(',', ''))
                        products.append(product)
            except Exception:
                continue
    
    # Fallback to text extraction
    if not products:
        price_matches = list(re.finditer(r'[¥￥]\s*([0-9.,]+)', html))
        for idx, pm in enumerate(price_matches[:30]):
            try:
                price = float(pm.group(1).replace(',', ''))
                start = max(0, pm.start() - 80)
                end = min(len(html), pm.end() + 80)
                context = _clean_text(html[start:end])
                
                # Try to extract title
                title = ""
                for p in [100, 80, 60]:
                    if start > 0:
                        text_before = _clean_text(html[max(0, start - p):start])
                        if len(text_before) > 10:
                            title = text_before[-50:].strip()
                            break
                if not title:
                    title = f"Product {idx+1} (Price: {price})"
                
                products.append({"title": title, "price": price, "raw_text": context})
            except Exception:
                continue
    
    return products[:20]


def _clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def search_trending_keywords() -> list[str]:
    defaults = [
        "美妆护肤", "家居日用", "食品饮料", "服饰穿搭",
        "母婴亲子", "数码家电", "运动户外", "珠宝配饰"
    ]
    return defaults