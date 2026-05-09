from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from typing import Any

from app.spiders.yiwugo import search_products as search_yiwugo

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

PLATFORM_PRIORITY = ["1688", "yiwugo", "buyin"]

PLATFORM_STATUS: dict[str, str] = {}


def _run_buyin_subprocess(keyword: str, limit: int, timeout: int = 120) -> list[dict[str, Any]]:
    script = os.path.join(SCRIPT_DIR, "buyin.py")
    cmd = ["uv", "run", "python", script, "--keyword", keyword, "--limit", str(limit)]
    logger.info(f"Buyin: Launching subprocess: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT_DIR, encoding="utf-8")
        if result.returncode != 0:
            logger.warning(f"Buyin subprocess exited with code {result.returncode}: {result.stderr[:200]}")
            return []
        out = result.stdout.strip()
        if not out:
            logger.warning("Buyin subprocess returned empty stdout")
            return []
        data = json.loads(out)
        if isinstance(data, list):
            logger.info(f"Buyin subprocess returned {len(data)} products")
            return data
        logger.warning(f"Buyin subprocess returned non-list data: {type(data)}")
        return []
    except subprocess.TimeoutExpired:
        logger.warning(f"Buyin subprocess timed out after {timeout}s")
        _kill_edge_processes()
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"Buyin subprocess JSON parse error: {e}")
        return []
    except Exception as e:
        logger.warning(f"Buyin subprocess failed: {e}")
        return []


def _run_1688_subprocess(keyword: str, limit: int, timeout: int = 120) -> list[dict[str, Any]]:
    script = os.path.join(SCRIPT_DIR, "alibaba1688.py")
    cmd = ["uv", "run", "python", script, "--keyword", keyword, "--limit", str(limit)]
    logger.info(f"1688: Launching subprocess: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT_DIR, encoding="utf-8")
        if result.returncode != 0:
            logger.warning(f"1688 subprocess exited with code {result.returncode}: {result.stderr[:200]}")
            return []
        out = result.stdout.strip()
        if not out:
            logger.warning("1688 subprocess returned empty stdout")
            return []
        data = json.loads(out)
        if isinstance(data, list):
            logger.info(f"1688 subprocess returned {len(data)} products")
            return data
        logger.warning(f"1688 subprocess returned non-list data: {type(data)}")
        return []
    except subprocess.TimeoutExpired:
        logger.warning(f"1688 subprocess timed out after {timeout}s")
        _kill_edge_processes()
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"1688 subprocess JSON parse error: {e}")
        return []
    except Exception as e:
        logger.warning(f"1688 subprocess failed: {e}")
        return []


def _kill_edge_processes():
    try:
        os.system("taskkill /F /IM msedge.exe >nul 2>&1")
    except Exception:
        pass


async def fetch_all_wholesale_data(
    keyword: str,
    limit_per_platform: int = 10,
    require_at_least: int = 1,
) -> dict[str, Any]:
    results: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str] = {}

    async def _search_buyin_wrapper(kw: str, lim: int):
        try:
            data = await asyncio.to_thread(_run_buyin_subprocess, kw, lim)
            results["buyin"] = data
            PLATFORM_STATUS["buyin"] = "ok" if data else "empty"
            logger.info(f"WholesaleAggregator: buyin returned {len(data)} products for '{kw}'")
        except Exception as e:
            errors["buyin"] = str(e)
            PLATFORM_STATUS["buyin"] = f"error: {e}"
            logger.warning(f"WholesaleAggregator: buyin failed: {e}")

    async def _search_1688_wrapper(kw: str, lim: int):
        try:
            data = await asyncio.to_thread(_run_1688_subprocess, kw, lim)
            results["1688"] = data
            PLATFORM_STATUS["1688"] = "ok" if data else "empty"
            logger.info(f"WholesaleAggregator: 1688 returned {len(data)} products for '{kw}'")
        except Exception as e:
            errors["1688"] = str(e)
            PLATFORM_STATUS["1688"] = f"error: {e}"
            logger.warning(f"WholesaleAggregator: 1688 failed: {e}")

    async def _search_yiwugo_wrapper(kw: str, lim: int):
        try:
            data = await asyncio.to_thread(search_yiwugo, keyword=kw, limit=lim)
            results["yiwugo"] = data
            PLATFORM_STATUS["yiwugo"] = "ok" if data else "empty"
            logger.info(f"WholesaleAggregator: yiwugo returned {len(data)} products for '{kw}'")
        except Exception as e:
            errors["yiwugo"] = str(e)
            PLATFORM_STATUS["yiwugo"] = f"error: {e}"
            logger.warning(f"WholesaleAggregator: yiwugo failed: {e}")

    tasks = [
        _search_yiwugo_wrapper(keyword, limit_per_platform),
    ]
    await asyncio.gather(*tasks)

    # 1688 and Buyin share the same Edge profile — run sequentially to avoid lock conflict
    await _search_1688_wrapper(keyword, limit_per_platform)
    await _search_buyin_wrapper(keyword, limit_per_platform)

    total_products = sum(len(v) for v in results.values())
    available_platforms = [p for p, d in results.items() if d]
    failed_platforms = list(errors.keys())
    empty_platforms = [p for p, d in results.items() if not d and p not in errors]

    if total_products < require_at_least:
        raise RuntimeError(
            f"Insufficient wholesale data: got {total_products} products from {available_platforms}, "
            f"need at least {require_at_least}. Failed: {failed_platforms}, Empty: {empty_platforms}"
        )

    merged = _merge_and_deduplicate(results)

    return {
        "products": merged,
        "sources": available_platforms,
        "failed_sources": failed_platforms,
        "empty_sources": empty_platforms,
        "errors": errors,
        "total_count": len(merged),
    }


async def fetch_priority_wholesale_data(
    keyword: str,
    limit: int = 20,
    require_at_least: int = 1,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    sources_used: list[str] = []
    errors: dict[str, str] = {}

    for platform in PLATFORM_PRIORITY:
        try:
            if platform == "1688":
                data = await asyncio.to_thread(_run_1688_subprocess, keyword, limit)
            elif platform == "buyin":
                data = await asyncio.to_thread(_run_buyin_subprocess, keyword, limit)
            elif platform == "yiwugo":
                data = await asyncio.to_thread(search_yiwugo, keyword=keyword, limit=limit)
            else:
                continue

            if data:
                results.extend(data)
                sources_used.append(platform)
                PLATFORM_STATUS[platform] = "ok"
                logger.info(f"WholesaleAggregator: {platform} returned {len(data)} products")
            else:
                PLATFORM_STATUS[platform] = "empty"
        except Exception as e:
            errors[platform] = str(e)
            PLATFORM_STATUS[platform] = f"error: {e}"
            logger.warning(f"WholesaleAggregator: {platform} failed: {e}")

        if len(results) >= limit:
            break

    if len(results) < require_at_least:
        raise RuntimeError(
            f"Insufficient wholesale data: got {len(results)} products from {sources_used}, "
            f"need at least {require_at_least}. Errors: {errors}"
        )

    merged = _merge_and_deduplicate({"mixed": results})

    return {
        "products": merged[:limit],
        "sources": sources_used,
        "failed_sources": list(errors.keys()),
        "errors": errors,
        "total_count": len(merged[:limit]),
    }


def get_platform_status() -> dict[str, str]:
    return dict(PLATFORM_STATUS)


def _merge_and_deduplicate(
    platform_results: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    all_products: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for platform, products in platform_results.items():
        for p in products:
            name = p.get("product_name", p.get("title", ""))
            if not name:
                continue

            normalized = _normalize_name(name)
            if normalized in seen_names:
                continue
            seen_names.add(normalized)

            product = dict(p)
            if "source" not in product:
                product["source"] = platform
            all_products.append(product)

    all_products.sort(key=lambda x: x.get("price_min", float("inf")))

    return all_products


def _normalize_name(name: str) -> str:
    import re
    n = re.sub(r'[\s\-_]', '', name)
    n = re.sub(r'[¥￥\d.,]', '', n)
    return n[:30].lower()


def format_platform_status(result: dict[str, Any]) -> str:
    parts: list[str] = []
    sources = set(result.get("sources", []))
    failed = set(result.get("failed_sources", []))
    empty = set(result.get("empty_sources", []))
    errors = result.get("errors", {})
    total = result.get("total_count", 0)

    for platform in ["1688", "yiwugo", "buyin"]:
        if platform in sources:
            count = sum(1 for p in result.get("products", []) if p.get("source") == platform)
            parts.append(f"\u2705 {platform}: {count}\u6761")
        elif platform in failed:
            err = errors.get(platform, "")
            if "captcha" in err.lower() or "\u9a8c\u8bc1" in err:
                parts.append(f"\u274c {platform}: \u9700\u8981\u624b\u52a8\u9a8c\u8bc1")
            elif "timeout" in err.lower() or "\u8d85\u65f6" in err:
                parts.append(f"\u274c {platform}: \u8d85\u65f6")
            else:
                parts.append(f"\u274c {platform}: \u5931\u8d25")
        elif platform in empty:
            parts.append(f"\u26a0\ufe0f {platform}: 0\u6761(\u7a7a)")
        else:
            parts.append(f"\u2795 {platform}: \u5f85\u5b9a")

    parts.append(f"\u2192 \u5171 {total} \u4ef6\u5546\u54c1")
    return " | ".join(parts)
