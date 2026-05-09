"""Explore Buyin picking library — can we search and get price data?"""
import sys, os, time, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'C:\liangtao\OpenCode\one_mini\ai-engine')
from app.config import settings
from playwright.sync_api import sync_playwright

EDGE = settings.edge_user_data
PROFILE = settings.edge_profile_dir

# Clean locks
for p in [rf'{PROFILE}\LOCK', rf'{PROFILE}\SingletonLock']:
    fp = os.path.join(EDGE, p)
    try:
        if os.path.isdir(fp):
            import shutil
            shutil.rmtree(fp, ignore_errors=True)
        elif os.path.exists(fp):
            os.remove(fp)
    except:
        pass
time.sleep(1)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=EDGE, headless=False, channel='msedge',
        args=['--disable-infobars', f'--profile-directory={PROFILE}'],
        locale='zh-CN', ignore_default_args=['--enable-automation'],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Navigate to picking library
    page.goto('https://buyin.jinritemai.com/dashboard/merch-picking-library',
              wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(10000)

    # Find all inputs
    inputs = page.evaluate("""
    () => {
        return Array.from(document.querySelectorAll('input')).map(i => ({
            type: i.type, placeholder: i.getAttribute('placeholder')||'',
            class: (i.className||'').substring(0, 80), id: i.id||'',
            visible: i.offsetParent !== null,
        }));
    }
    """)
    print(f"Found {len(inputs)} inputs:")
    for inp in inputs:
        print(f"  type={inp['type']} ph=\"{inp['placeholder']}\" visible={inp['visible']} class={inp['class'][:60]}")

    # Get page title and body text
    title = page.title()
    body = page.evaluate("document.body.innerText.substring(0, 1000)")
    print(f"\nTitle: {title[:120]}")
    print(f"URL: {page.url[:150]}")
    print(f"Body contains '手机壳': {'手机壳' in body}")
    print(f"Body snippet:\n{body[:500]}")

    # If there's a search input, try to use it
    search = page.query_selector('input[placeholder*="搜索"], input[placeholder*="输入"], input[type="text"]')
    if search:
        print("\nFound search input! Typing...")
        search.click()
        page.wait_for_timeout(500)
        search.fill("手机壳")
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(8000)
        body2 = page.evaluate("document.body.innerText.substring(0, 2000)")
        print(f"After search body:\n{body2[:800]}")

    ctx.close()
    print("Done")
