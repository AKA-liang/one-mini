"""
Alibaba 1688 spider — wholesale supply data source.
Subprocess mode: python app/spiders/alibaba1688.py --keyword "xxx" --limit 20
Outputs JSON to stdout.
"""
from __future__ import annotations

import os as _os, sys as _sys
if __name__ == "__main__":
    _os.chdir(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    _sys.path.insert(0, _os.getcwd())

import argparse
import json
import logging
import os
import re
import sys
import time
from typing import Any
from urllib.parse import quote

from app.config import settings

logger = logging.getLogger(__name__)

ALIBABA_1688_BASE_URL = "https://s.1688.com"

_CAPTCHA_DETECT_JS = """
() => {
    const body = document.body.innerText || '';
    const captchaKeywords = ['验证码', '滑动验证', '请验证', '拖动滑块'];
    const hasKeyword = captchaKeywords.some(k => body.includes(k));
    const el = document.querySelector('.nc-lang-cnt, #nc_1_n1z, [id*="nocaptcha"], .captcha, .slider, .verify');
    return hasKeyword || (el !== null);
}
"""

_CONTENT_READY_JS = """
() => document.querySelectorAll('.search-offer-item, [class*="search-offer-item"]').length
"""

_CAPTCHA_WARNING = """
╔══════════════════════════════════════════════════╗
║  ⚠️  1688 检测到滑动验证                         ║
║  请在打开的 Edge 浏览器窗口中手动完成验证         ║
║  完成后商品数据将自动提取，最多等待 120 秒...     ║
╚══════════════════════════════════════════════════╝
"""

_CAPTCHA_TIMEOUT_MSG = """
⚠️  1688 验证超时 (120s)，本次获取失败。
    下次选品时请及时完成验证。
"""


def _detect_captcha(page) -> bool:
    try:
        url = page.url
        if "x5sec" in url.lower():
            return True
        result = page.evaluate(_CAPTCHA_DETECT_JS)
        return bool(result)
    except Exception:
        return False


def _wait_for_user_verification(page, timeout: int = 120) -> bool:
    print(_CAPTCHA_WARNING, file=sys.stderr, flush=True)
    logger.warning("1688: Captcha detected, waiting for manual verification (max %ds)...", timeout)

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        try:
            has_captcha = page.evaluate(_CAPTCHA_DETECT_JS)
            item_count = page.evaluate(_CONTENT_READY_JS)
            if not has_captcha and item_count > 0:
                logger.info("1688: Verification passed! Found %d offer items on page.", item_count)
                print(f"[16:08] ✅ 验证通过，已加载 {item_count} 个商品", file=sys.stderr, flush=True)
                return True
        except Exception:
            pass

    logger.warning("1688: Verification timeout after %ds", timeout)
    print(_CAPTCHA_TIMEOUT_MSG, file=sys.stderr, flush=True)
    return False


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


def _build_search_url(keyword: str, page: int = 1, sort: str = "") -> str:
    try:
        gbk_keyword = quote(keyword.encode("gbk", errors="replace"))
    except Exception:
        gbk_keyword = quote(keyword)
    params = f"keywords={gbk_keyword}"
    if page > 1:
        params += f"&beginPage={page}"
    if sort:
        params += f"&sortType={sort}"
    return f"{ALIBABA_1688_BASE_URL}/selloffer/offer_search.htm?{params}"


def _parse_price_text(text: str) -> tuple[float, float] | None:
    numbers = re.findall(r"[\d.]+", text)
    if len(numbers) >= 2:
        prices = [float(n) for n in numbers]
        return min(prices), max(prices)
    elif len(numbers) == 1:
        p = float(numbers[0])
        return p, p
    return None


_PAGE_EXTRACT_JS = """
() => {
    const items = document.querySelectorAll('.search-offer-item, [class*="search-offer-item"]');
    const results = [];
    for (const el of items) {
        if (results.length >= 20) break;

        // Title
        const titleEl = el.querySelector('[class*="title"], [class*="subject"], .offer-title, .offer_subject, h3');
        const title = titleEl ? titleEl.textContent.trim() : '';

        // Price
        const priceEl = el.querySelector('[class*="price"], .price, .offer-price');
        const priceText = priceEl ? priceEl.textContent.trim() : '';

        // Shop
        const shopEl = el.querySelector('[class*="company"], [class*="supplier"], [class*="shop"], [class*="seller"]');
        const shop = shopEl ? shopEl.textContent.replace('旺旺在线','').trim() : '';

        // Product detail link (not similar search)
        let detailLink = '';
        const links = el.querySelectorAll('a[href*="detail.1688.com"]');
        if (links.length > 0) {
            detailLink = links[links.length - 1].href;
        } else {
            const mainLink = el.querySelector('a[href*="offer"]');
            if (mainLink) detailLink = mainLink.href;
        }

        // Image
        const imgEl = el.querySelector('img[src*="cdn."], img[src*="img."], img');
        const image = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';

        // MOQ
        const moqEl = el.querySelector('[class*="minOrder"], [class*="moq"], [class*="trade"]');
        const moqText = moqEl ? moqEl.textContent.trim() : '';

        // Sales
        const salesEl = el.querySelector('[class*="sale"], [class*="sold"]');
        const salesText = salesEl ? salesEl.textContent.trim() : '';

        if (title) {
            results.push({
                title: title.substring(0, 200),
                priceText: priceText,
                shop: shop.substring(0, 60),
                link: detailLink,
                image: image,
                moqText: moqText,
                salesText: salesText,
            });
        }
    }
    return results;
}
"""


def search_products(keyword: str, page: int = 1, sort: str = "", limit: int = 20) -> list[dict[str, Any]]:
    if not settings.persistent_context_available:
        logger.info("1688: Server mode — persistent_context unavailable, skipping")
        return []
    url = _build_search_url(keyword, page, sort)
    logger.info(f"1688: Searching for '{keyword}' at {url}")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=settings.edge_user_data,
                headless=False,
                channel="msedge",
                args=[
                    "--disable-infobars",
                    f"--profile-directory={settings.edge_profile_dir}",
                ],
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                ignore_default_args=["--enable-automation"],
            )

            page = context.pages[0] if context.pages else context.new_page()

            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)

            logger.info("1688: Navigating...")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                page.goto(url, wait_until="load", timeout=60000)

            page.wait_for_timeout(3000)

            current_url = page.url
            if "login" in current_url.lower():
                logger.warning("1688: Redirected to login")
                context.close()
                return []

            if _detect_captcha(page):
                if not _wait_for_user_verification(page):
                    context.close()
                    return []
                page.wait_for_timeout(2000)

            for _ in range(4):
                page.mouse.wheel(0, 800)
                page.wait_for_timeout(1200)
            page.wait_for_timeout(2000)

            raw_items = page.evaluate(_PAGE_EXTRACT_JS)
            context.close()

            if not raw_items or not isinstance(raw_items, list):
                item_count = page.evaluate(_CONTENT_READY_JS)
                if item_count == 0:
                    print("⚠️  1688 未检测到商品数据，可能需要手动验证或刷新页面", file=sys.stderr, flush=True)

    except Exception as e:
        logger.warning(f"1688: Playwright failed: {e}")
        return []

    if not raw_items or not isinstance(raw_items, list):
        logger.info("1688: No items extracted from page")
        return []

    products = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        if not title:
            continue

        product = {
            "product_name": title[:200],
            "source": "1688",
        }

        price_text = item.get("priceText", "")
        if price_text:
            parsed = _parse_price_text(price_text)
            if parsed:
                product["price_min"], product["price_max"] = parsed

        shop = item.get("shop", "")
        if shop:
            product["shop_name"] = shop

        link = item.get("link", "")
        if link and link.startswith("//"):
            link = f"https:{link}"
        if link:
            product["product_url"] = link

        image = item.get("image", "")
        if image and image.startswith("//"):
            image = f"https:{image}"
        if image:
            product["image_url"] = image

        moq_text = item.get("moqText", "")
        if moq_text:
            moq_match = re.search(r"(\d+)", moq_text)
            if moq_match:
                product["moq"] = int(moq_match.group(1))

        products.append(product)

    logger.info(f"1688: Parsed {len(products)} products")
    return products[:limit]


if __name__ == "__main__":
    _os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--sort", default="")
    args = parser.parse_args()

    _delete_lock_files()
    time.sleep(1)

    result = search_products(keyword=args.keyword, limit=args.limit, page=args.page, sort=args.sort)
    print(json.dumps(result, ensure_ascii=False))
