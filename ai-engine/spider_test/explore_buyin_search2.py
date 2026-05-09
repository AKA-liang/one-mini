"""Buyin picking library: search for product, extract price/commission data."""
import sys, os, time, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\liangtao\OpenCode\one_mini\ai-engine')
from app.config import settings
from playwright.sync_api import sync_playwright

EDGE = settings.edge_user_data
PROFILE = settings.edge_profile_dir

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

    # Navigate + wait
    page.goto('https://buyin.jinritemai.com/dashboard/merch-picking-library',
              wait_until='domcontentloaded', timeout=45000)
    page.wait_for_timeout(10000)

    # Find search by class
    search = page.query_selector('.auxo-input, input[type="search"]')
    if search:
        print("Found search input! Searching for 手机壳...")
        search.click()
        page.wait_for_timeout(1000)
        search.fill("手机壳")
        page.wait_for_timeout(1000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(10000)

        # Extract results from page
        body = page.evaluate("document.body.innerText.substring(0, 3000)")
        print(f"\nAfter search body ({len(body)} chars):")
        # Write to file to avoid encoding issues
        with open("buyin_output.txt", "w", encoding="utf-8") as f:
            f.write(body)
        print("Written to buyin_output.txt")

        # Also try to extract product cards
        cards = page.evaluate("""
        () => {
            const cards = document.querySelectorAll('[class*="card"], [class*="item"], [class*="product"]');
            return Array.from(cards).slice(0, 10).map(c => ({
                text: (c.textContent || '').trim().substring(0, 300),
                className: (c.className || '').substring(0, 80),
            }));
        }
        """)
        print(f"\nFound {len(cards)} product cards:")
        for c in cards:
            print(f"  [{c['className'][:40]}] {c['text'][:150]}")
    else:
        print("Search input not found!")
        page.screenshot(path="screenshot_buyin.png")

    ctx.close()
    print("Done")
