from __future__ import annotations

from app.config import settings


def is_cookie_valid(cookie_str: str) -> bool:
    """Check if cookie string is non-empty and has valid key-value pairs."""
    if not cookie_str or not isinstance(cookie_str, str):
        return False
    parts = [p.strip() for p in cookie_str.split(";") if p.strip()]
    if len(parts) < 1:
        return False
    # At least one key=value pair should exist
    has_valid = any("=" in p and len(p.split("=", 1)[1].strip()) > 0 for p in parts)
    return has_valid


def get_chanmama_cookies() -> list[dict[str, str]]:
    cookie_str = settings.chanmama_cookie
    if not is_cookie_valid(cookie_str):
        return []
    return _parse_cookie_string_to_list(cookie_str, ".chanmama.com")


def get_alibaba_1688_cookies() -> list[dict[str, str]]:
    cookie_str = settings.alibaba_1688_cookie
    if not cookie_str:
        return []
    return _parse_cookie_string_to_list(cookie_str, ".1688.com")


def get_yiwugo_cookies() -> list[dict[str, str]]:
    cookie_str = settings.yiwugo_cookie
    if not cookie_str:
        return []
    return _parse_cookie_string_to_list(cookie_str, ".yiwugo.com")


def get_chanmama_cookie_string() -> str:
    return settings.chanmama_cookie


def get_alibaba_1688_cookie_string() -> str:
    return settings.alibaba_1688_cookie


def get_yiwugo_cookie_string() -> str:
    return settings.yiwugo_cookie


def has_chanmama_cookies() -> bool:
    return is_cookie_valid(settings.chanmama_cookie)


def has_alibaba_cookies() -> bool:
    return is_cookie_valid(settings.alibaba_1688_cookie)


def has_yiwugo_cookies() -> bool:
    return is_cookie_valid(settings.yiwugo_cookie)


def has_buyin_cookies() -> bool:
    return is_cookie_valid(settings.buyin_cookie)


def _parse_cookie_string_to_list(cookie_str: str, domain: str) -> list[dict[str, str]]:
    cookies: list[dict[str, str]] = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
            })
    return cookies


def _parse_cookie_string(cookie_str: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies[name.strip()] = value.strip()
    return cookies


def detect_auth_failure(url: str = "", page_text: str = "", status_code: int = 0) -> dict | None:
    if status_code in (401, 403):
        return {"status": status_code, "url": url,
                "reason": "HTTP Auth Required" if status_code == 401 else "HTTP Forbidden"}
    login_patterns = [
        "login", "Login", "请先登录", "请登录", "您还未登录",
        "需要登录", "session expired", "unauthorized",
    ]
    for pat in login_patterns:
        if pat in page_text:
            return {"url": url, "reason": f"Login required (matched '{pat}')"}
    if url and "login" in url.lower() and "logging" not in url.lower():
        return {"url": url, "reason": "Redirected to login page"}
    return None