from __future__ import annotations

from app.config import settings


def get_chanmama_cookies() -> list[dict[str, str]]:
    cookie_str = settings.chanmama_cookie
    if not cookie_str:
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
    return bool(settings.chanmama_cookie)


def has_alibaba_cookies() -> bool:
    return bool(settings.alibaba_1688_cookie)


def has_yiwugo_cookies() -> bool:
    return bool(settings.yiwugo_cookie)


def get_buyin_cookie_string() -> str:
    return settings.buyin_cookie


def has_buyin_cookies() -> bool:
    return bool(settings.buyin_cookie)


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