"""
本地爬虫测试脚本 - 1688插件CSV自动导出
使用方法：在本地电脑运行
  python test_1688_plugin.py

功能：
  1. 用Playwright加载Edge Profile（含1688采购助手插件）
  2. 打开1688搜索页
  3. 查找插件注入的UI元素
  4. 尝试触发插件导出
  5. 监控下载目录中的CSV文件
"""
import asyncio
import json
import sys
import time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请先安装playwright: pip install playwright && playwright install")
    sys.exit(1)

EDGE_USER_DATA = r"C:\Users\13265\AppData\Local\Microsoft\Edge\User Data"
EDGE_PROFILE = "Profile 1"
PLUGIN_ID = "pmboidfffhijmecmhpmgpmnkjamipkdo"

DOWNLOAD_DIR = Path(r"C:\Users\13265\Downloads")
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

EXISTING_FILES: set[str] = set()


def _snapshot_downloads() -> set[str]:
    return {f.name for f in DOWNLOAD_DIR.glob("*.csv") if f.is_file()}


async def test_1688_plugin():
    global EXISTING_FILES
    print("=" * 60)
    print("1688插件CSV自动导出测试 - Local Spider Test")
    print("=" * 60)

    EXISTING_FILES = _snapshot_downloads()
    print(f"下载目录现有CSV文件: {len(EXISTING_FILES)}")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=EDGE_USER_DATA,
            headless=False,
            channel="msedge",
            args=[
                f"--profile-directory={EDGE_PROFILE}",
                f"--disable-extensions-except={EDGE_USER_DATA}\\{EDGE_PROFILE}\\Extensions\\{PLUGIN_ID}\\1.1.1_0",
                f"--load-extension={EDGE_USER_DATA}\\{EDGE_PROFILE}\\Extensions\\{PLUGIN_ID}\\1.1.1_0",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1400, "height": 900},
            accept_downloads=True,
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        # 1. 访问1688搜索页
        print("\n[Step 1] 访问1688搜索页...")
        search_url = "https://s.1688.com/selloffer/offer_search.htm?keywords=T恤"
        try:
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(5000)
            title = await page.title()
            print(f"  title: {title}")
            print(f"  url: {page.url}")

            # 检查是否被验证码拦截
            content = await page.content()
            if "验证" in content[:3000] or "x5sec" in content:
                print("  ⚠️ 检测到验证码拦截")
            else:
                print("  ✅ 页面加载成功，无验证码")
        except Exception as e:
            print(f"  ❌ 访问失败: {e}")

        # 2. 检查插件注入的元素
        print("\n[Step 2] 检查插件注入的UI元素...")
        plugin_selectors = [
            "[class*='ai-pick']",
            "[class*='aipick']",
            "[class*='plugin-1688']",
            "[data-plugin='1688']",
            "#ai-pick-btn",
            ".ai-find-btn",
            "[class*='export']",
            "[class*='csv']",
            "button:has-text('导出')",
            "button:has-text('Export')",
            "button:has-text('AI选品')",
        ]

        found_elements: list[str] = []
        for selector in plugin_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    found_elements.append(selector)
                    print(f"  ✅ 找到: {selector} ({len(elements)}个)")
                    for el in elements[:2]:
                        text = await el.inner_text()
                        print(f"      text: {text[:100]}")
            except Exception:
                pass

        if not found_elements:
            print("  ⚠️ 未找到插件注入的UI元素")
            print("  可能原因：插件需要手动启用、页面未完全加载、或插件不在此页面激活")

        # 3. 检查插件的后台页面
        print("\n[Step 3] 检查插件后台页面...")
        try:
            bg_pages = context.background_pages
            for i, bg in enumerate(bg_pages):
                print(f"  后台页面 {i}: {bg.url[:120]}")
        except Exception as e:
            print(f"  检查后台页面失败: {e}")

        # 4. 尝试通过window.postMessage与插件通信
        print("\n[Step 4] 尝试与插件通信...")
        try:
            result = await page.evaluate("""
                () => {
                    // 检查插件是否在window上注册了任何对象
                    const pluginKeys = [];
                    for (const key of Object.keys(window)) {
                        if (key.toLowerCase().includes('plugin') || 
                            key.toLowerCase().includes('1688') ||
                            key.toLowerCase().includes('aipick') ||
                            key.toLowerCase().includes('export')) {
                            pluginKeys.push(key);
                        }
                    }
                    return { pluginKeys, hasReact: !!window.__REACT_DEVTOOLS_GLOBAL_HOOK__ };
                }
            """)
            print(f"  window上的插件相关key: {result}")
        except Exception as e:
            print(f"  执行JS失败: {e}")

        # 5. 截图
        screenshot_file = OUTPUT_DIR / "1688_plugin.png"
        await page.screenshot(path=str(screenshot_file), full_page=False)
        print(f"\n已保存截图: {screenshot_file}")

        # 6. 保存HTML
        html_content = await page.content()
        html_file = OUTPUT_DIR / "1688_plugin.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"已保存HTML: {html_file}")

        await context.close()

    print("\n" + "=" * 60)
    print("测试完成")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_1688_plugin())
