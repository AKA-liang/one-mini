"""
Buyin 自助诊断 - 请在本地运行（需关闭 Edge 后执行）
   uv run python spider_test/diag_buyin_self.py

此脚本会：打开选品库 → 等20秒 → 输出所有 input 元素信息
你把输出里搜索框那行的 placeholder/class/id 告诉我，我改选择器。
"""
import os, sys, time, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

EDGE = r'C:\Users\13265\AppData\Local\Microsoft\Edge\User Data'

os.system('taskkill /F /IM msedge.exe >nul 2>&1')
time.sleep(2)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=EDGE, headless=False, channel='msedge',
        args=['--disable-blink-features=AutomationControlled', '--no-sandbox',
              '--profile-directory=Profile 1'],
        locale='zh-CN', ignore_default_args=['--enable-automation'],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print('1) 导航到选品库...')
    page.goto('https://buyin.jinritemai.com/dashboard/merch-picking-library',
              wait_until='domcontentloaded', timeout=45000)
    print(f'   当前 URL: {page.url[:120]}')

    print('2) 等待 SPA 渲染 (20s)...')
    for i in range(20, 0, -5):
        time.sleep(5)
        inputs = page.evaluate('document.querySelectorAll("input").length')
        print(f'   {i}s left - 已发现 {inputs} 个 input 元素')

    print('\n3) 枚举所有 input:')
    info = page.evaluate("""
    () => Array.from(document.querySelectorAll('input')).map((i, idx) => ({
        index: idx,
        type: i.type,
        placeholder: i.getAttribute('placeholder') || '',
        class: (i.className || '').substring(0, 120),
        id: i.id || '',
        name: i.getAttribute('name') || '',
        visible: i.offsetParent !== null,
        value: (i.value || '').substring(0, 40),
        rect: JSON.stringify(i.getBoundingClientRect()),
    }))
    """)

    for inp in info:
        print(f"\n  [{inp['index']}] type={inp['type']} placeholder={inp['placeholder']}")
        print(f"      class={inp['class']}")
        print(f"      id={inp['id']} name={inp['name']}")
        print(f"      visible={inp['visible']} value={inp['value']}")

    print('\n4) 搜索相关元素:')
    search = page.evaluate("""
    () => {
        const results = [];
        document.querySelectorAll('[class*="search"], [class*="Search"], '
            + '[class*="query"], [class*="Query"], '
            + 'input[placeholder*="搜索"], input[placeholder*="输入"], '
            + 'input[placeholder*="商品"], input[placeholder*="名称"], '
            + 'input[type="text"], input[type="search"]').forEach(el => {
            results.push({
                tag: el.tagName,
                text: (el.textContent || '').trim().substring(0, 60),
                placeholder: el.getAttribute('placeholder') || '',
                class: (el.className || '').substring(0, 120),
                id: el.id || '',
                visible: el.offsetParent !== null,
                outerHTML: el.outerHTML.substring(0, 300),
            });
        });
        return results;
    }
    """)

    if search:
        for s in search:
            print(f'\n  tag={s["tag"]} text={s["text"]}')
            print(f'  placeholder={s["placeholder"]} id={s["id"]}')
            print(f'  class={s["class"]}')
            print(f'  visible={s["visible"]}')
            print(f'  HTML: {s["outerHTML"]}')
    else:
        print('  (未找到搜索相关元素)')

    print('\n5) URL 和标题:')
    print(f'  URL: {page.url[:200]}')
    print(f'  Title: {page.title()[:120]}')

    ctx.close()
    print('\n完成。请把上面的输出内容发给我。')
