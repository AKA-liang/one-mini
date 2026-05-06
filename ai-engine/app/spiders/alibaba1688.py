from __future__ import annotations

import json
import logging
import re
from typing import Any

from scrapling.fetchers import StealthyFetcher, DynamicFetcher, Fetcher

from app.spiders.cookie_manager import (
    get_alibaba_1688_cookies,
    get_alibaba_1688_cookie_string,
    has_alibaba_cookies,
)

logger = logging.getLogger(__name__)

ALIBABA_1688_BASE_URL = "https://s.1688.com"


def search_products(
    keyword: str,
    page: int = 1,
    sort: str = "",
) -> list[dict[str, Any]]:
    strategies = []
    if has_alibaba_cookies():
        strategies.append(lambda: _fetch_with_cookies(keyword, page, sort))
    strategies.extend([
        lambda: _fetch_with_stealthy(keyword, page, sort),
        lambda: _fetch_with_dynamic(keyword, page, sort),
        lambda: _fetch_with_http(keyword, page, sort),
    ])

    for strategy in strategies:
        try:
            result = strategy()
            if result:
                logger.info(f"1688: strategy returned {len(result)} products for '{keyword}'")
                return result
        except Exception as e:
            logger.warning(f"1688: strategy failed: {e}")
            continue

    logger.info(f"1688: All strategies failed for '{keyword}', using mock data")
    return _generate_mock_results(keyword)


def _fetch_with_cookies(keyword: str, page: int = 1, sort: str = "") -> list[dict[str, Any]]:
    url = _build_search_url(keyword, page, sort)
    cookies = get_alibaba_1688_cookies()

    page_data = StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=True,
        cookies=cookies,
        timeout=30000,
    )

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "login" in current_url.lower():
        logger.info("1688: Still redirected to login after cookie injection")
        return []

    return _parse_search_page(page_data)


def _fetch_with_stealthy(keyword: str, page: int = 1, sort: str = "") -> list[dict[str, Any]]:
    url = _build_search_url(keyword, page, sort)
    page_data = StealthyFetcher.fetch(
        url, headless=True, network_idle=True, timeout=30000
    )

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "login" in current_url.lower() or "register" in current_url.lower():
        logger.info("1688: Redirected to login page, skipping")
        return []

    return _parse_search_page(page_data)


def _fetch_with_dynamic(keyword: str, page: int = 1, sort: str = "") -> list[dict[str, Any]]:
    url = _build_search_url(keyword, page, sort)
    page_data = DynamicFetcher.fetch(
        url, headless=True, network_idle=True, timeout=30000
    )

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "login" in current_url.lower() or "register" in current_url.lower():
        logger.info("1688: Redirected to login page, skipping")
        return []

    return _parse_search_page(page_data)


def _fetch_with_http(keyword: str, page: int = 1, sort: str = "") -> list[dict[str, Any]]:
    url = _build_search_url(keyword, page, sort)
    page_data = Fetcher.get(url, stealthy_headers=True)

    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "login" in current_url.lower() or "register" in current_url.lower():
        logger.info("1688: Redirected to login page (HTTP), skipping")
        return []

    return _try_extract_from_js_data(page_data)


def _build_search_url(keyword: str, page: int = 1, sort: str = "") -> str:
    params = f"keywords={keyword}"
    if page > 1:
        params += f"&beginPage={page}"
    if sort:
        params += f"&sortType={sort}"
    return f"{ALIBABA_1688_BASE_URL}/selloffer/offer_search.htm?{params}"


def _parse_search_page(page_data: Any) -> list[dict[str, Any]]:
    current_url = page_data.url if hasattr(page_data, "url") else ""
    if "login" in current_url.lower() or "register" in current_url.lower():
        return []

    js_products = _try_extract_from_js_data(page_data)
    if js_products:
        return js_products

    products: list[dict[str, Any]] = []

    offer_items = (
        page_data.css(".offer-item")
        or page_data.css(".sw-offer-item")
        or page_data.css("[class*='offer-card']")
        or page_data.css("[class*='offer-item']")
    )

    if not offer_items:
        offer_items = page_data.find_all(
            "div", class_=re.compile(r"offer|item|product|card", re.I)
        )

    for item in offer_items[:20]:
        try:
            product = _extract_product_from_element(item)
            if product and product.get("product_name"):
                products.append(product)
        except Exception:
            continue

    return products


def _try_extract_from_js_data(page_data: Any) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    if not hasattr(page_data, "css"):
        return products

    scripts = page_data.css("script::text").getall()
    all_script = " ".join(scripts)

    offer_match = re.search(
        r"offerresultData\s*=\s*({.*?})(?:\s*;|\s*window)",
        all_script, re.DOTALL,
    )
    if not offer_match:
        offer_match = re.search(
            r"window\.data\s*=\s*({.*?})(?:\s*;|\s*</)",
            all_script, re.DOTALL,
        )

    if offer_match:
        try:
            raw = offer_match.group(1)
            data = json.loads(raw)
            offer_list = data.get("offerList", []) if isinstance(data, dict) else []
            for item in offer_list[:20]:
                product: dict[str, Any] = {
                    "product_name": str(item.get("subject", item.get("title", "")))[:200],
                    "source": "1688",
                }

                price_info = item.get("price", "")
                if isinstance(price_info, str):
                    price_range = _parse_price_range(price_info)
                    if price_range:
                        product.update(price_range)
                elif isinstance(price_info, dict):
                    product["price_min"] = float(price_info.get("min", price_info.get("begin", 0)))
                    product["price_max"] = float(price_info.get("max", price_info.get("end", 0)))

                moq = item.get("minOrderQuantity", item.get("moq", 0))
                product["moq"] = int(moq) if moq else None

                product["shop_name"] = str(item.get("company", item.get("shopName", "")))

                product_url = item.get("offerLink", item.get("url", ""))
                if product_url:
                    if str(product_url).startswith("//"):
                        product_url = f"https:{product_url}"
                    product["product_url"] = str(product_url)

                if product.get("product_name"):
                    products.append(product)
        except (json.JSONDecodeError, Exception):
            pass

    return products


def _extract_product_from_element(element: Any) -> dict[str, Any] | None:
    product: dict[str, Any] = {}

    name = ""
    if hasattr(element, "css"):
        name_els = element.css(".title::text,.offer-title::text,.subject::text,a[class*='title']::text")
        if name_els:
            first = name_els[0] if isinstance(name_els, list) else name_els
            name = str(first).strip() if first else ""
    if not name and hasattr(element, "css"):
        name = str(element.css("a::text").get() or "").strip()

    if not name:
        return None

    product["product_name"] = name[:200]

    if hasattr(element, "css"):
        price_els = element.css(".price::text,.offer-price::text,[class*='price']::text")
        if price_els:
            price_text = str(price_els[0]).strip() if isinstance(price_els, list) else str(price_els).strip()
            price_range = _parse_price_range(price_text)
            if price_range:
                product.update(price_range)
            else:
                price_match = re.search(r"[\d.]+", price_text)
                if price_match:
                    product["price_min"] = float(price_match.group())
                    product["price_max"] = float(price_match.group())

    if hasattr(element, "css"):
        moq_els = element.css(".moq::text,[class*='min-order']::text,[class*='moq']::text")
        if moq_els:
            moq_text = str(moq_els[0]).strip() if isinstance(moq_els, list) else str(moq_els).strip()
            moq_match = re.search(r"(\d+)", moq_text)
            product["moq"] = int(moq_match.group(1)) if moq_match else None

    if hasattr(element, "css"):
        shop_els = element.css(".shop-name::text,[class*='shop']::text,[class*='store']::text")
        if shop_els:
            product["shop_name"] = str(shop_els[0]).strip() if isinstance(shop_els, list) else str(shop_els).strip()

    if hasattr(element, "css"):
        link_els = element.css("a::attr(href)")
        if link_els:
            link = str(link_els[0]) if isinstance(link_els, list) else str(link_els)
            if link and not link.startswith("javascript"):
                if link.startswith("//"):
                    link = f"https:{link}"
                elif link.startswith("/"):
                    link = f"https://detail.1688.com{link}"
                product["product_url"] = link

    product["source"] = "1688"
    return product


def _parse_price_range(price_str: str) -> dict[str, float] | None:
    prices = re.findall(r"[\d.]+", price_str)
    if len(prices) >= 2:
        return {"price_min": float(prices[0]), "price_max": float(prices[-1])}
    elif len(prices) == 1:
        p = float(prices[0])
        return {"price_min": p, "price_max": p}
    return None


def _generate_mock_results(keyword: str) -> list[dict[str, Any]]:
    import random

    mock_products: list[dict[str, Any]] = []
    categories = {
        "保温杯": {"base_price": 15, "moq": 50},
        "手机壳": {"base_price": 3, "moq": 100},
        "瑜伽裤": {"base_price": 25, "moq": 30},
        "面膜": {"base_price": 5, "moq": 200},
        "蓝牙耳机": {"base_price": 30, "moq": 20},
    }

    base_info = categories.get(keyword, {"base_price": 20, "moq": 50})
    base_price = base_info["base_price"]
    base_moq = base_info["moq"]

    for i in range(5):
        price_min = round(base_price * (0.8 + random.random() * 0.4), 2)
        price_max = round(price_min * (1.5 + random.random()), 2)
        mock_products.append({
            "product_name": f"{keyword}批发 厂家直供 款式{i + 1}",
            "price_min": price_min,
            "price_max": price_max,
            "moq": base_moq + i * 10,
            "shop_name": f"义乌市{keyword}源头工厂店",
            "source": "1688_mock",
            "product_url": f"https://detail.1688.com/offer/mock_{keyword}_{i + 1}.html",
        })

    return mock_products