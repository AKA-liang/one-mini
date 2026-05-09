"""Diagnose Buyin page after cookie login"""
import sys, os, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from playwright.sync_api import sync_playwright
from app.spiders.cookie_manager import get_buyin_cookie_string

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False)
    ctx = browser.new_context(locale="zh-CN")
    cs = get_buyin_cookie_string()
    cookies = []
    for part in cs.split("; "):
        if "=" in part:
            n, v = part.split("=", 1)
            cookies.append({"name": n, "value": v, "domain": ".jinritemai.com", "path": "/"})
    ctx.add_cookies(cookies)
    page = ctx.new_page()

    page.goto("https://buyin.jinritemai.com/dashboard/merch-picking-library",
              wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(8000)

    url = page.url
    title = page.title()
    print(f"URL: {url[:150]}")
    print(f"Title: {title[:100]}")
    print(f"Contains 'login': {'login' in url.lower() or 'passport' in url.lower()}")

    # Find all inputs
    inputs = page.evaluate("""
    () => Array.from(document.querySelectorAll('input, [contenteditable="true"]')).map(e => ({
        tag: e.tagName, type: e.type || '', placeholder: e.getAttribute('placeholder')||'',
        class: (e.className||'').substring(0,80), id: e.id||'', visible: e.offsetParent !== null,
    }))
    """)
    print(f"Inputs found: {len(inputs)}")
    for i, inp in enumerate(inputs):
        print(f"  [{i}] {inp['tag']} type={inp['type']} ph={inp['placeholder'][:40]} class={inp['class'][:60]} visible={inp['visible']}")

    # Body snippet
    body = page.evaluate("document.body.innerText.substring(0, 800)")
    print(f"\nBody: {body[:400]}")

    browser.close()
    print("Done")
