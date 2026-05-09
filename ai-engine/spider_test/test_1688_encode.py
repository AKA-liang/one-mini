"""Test 1688 URL encoding directly"""
import os, sys, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'C:\liangtao\OpenCode\one_mini\ai-engine')

from urllib.parse import quote
from playwright.sync_api import sync_playwright

EDGE = r'C:\Users\13265\AppData\Local\Microsoft\Edge\User Data'

os.system('taskkill /F /IM msedge.exe >nul 2>&1')
for p in ['Profile 1\\LOCK', 'Profile 1\\SingletonLock']:
    fp = os.path.join(EDGE, p)
    try:
        if os.path.isdir(fp): import shutil; shutil.rmtree(fp, ignore_errors=True)
        elif os.path.exists(fp): os.remove(fp)
    except: pass
time.sleep(2)

keyword = "抖音热销"
encoded = quote(keyword)
url = f"https://s.1688.com/selloffer/offer_search.htm?keywords={encoded}"

print(f"Keyword: {keyword}")
print(f"Encoded: {encoded}")
print(f"URL:     {url}")

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=EDGE, headless=False, channel='msedge',
        args=['--disable-infobars', '--profile-directory=Profile 1'],
        locale='zh-CN', ignore_default_args=['--enable-automation'],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(5000)

    # Check what's in the search input box
    search_val = page.evaluate("""
    () => {
        const input = document.querySelector('input[name*="keyword"], input.search-input, input[type="text"]');
        return input ? input.value.substring(0, 30) : 'no input found';
    }
    """)
    
    # Also check the page's character encoding
    encoding = page.evaluate("document.characterSet")
    page_title = page.title()[:80]

    print(f"Page encoding: {encoding}")
    print(f"Page title:    {page_title}")
    print(f"Search input value: {search_val}")
    print(f"Search input repr: {repr(search_val)}")

    ctx.close()
