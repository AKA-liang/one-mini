"""
Capture buyin product APIs by hooking into existing browser tab.
Strategy: intercept XHR/fetch from the page's JavaScript context.
"""
import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


async def hook_buyin_xhr():
    print("=" * 60)
    print("Buyin XHR Hook - Capture from existing tab")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        # Find existing buyin page or create one
        buyin_page = None
        for pg in context.pages:
            if "buyin" in pg.url:
                buyin_page = pg
                print(f"Found existing buyin tab: {pg.url[:80]}")
                break

        if not buyin_page:
            buyin_page = await context.new_page()
            await buyin_page.goto("https://buyin.jinritemai.com/dashboard/service/selection/square", wait_until="networkidle", timeout=60000)
            await buyin_page.wait_for_timeout(8000)
            print(f"Created new tab: {buyin_page.url[:80]}")

        # Inject XHR/fetch interceptor
        print("\n[Step 1] Injecting XHR/fetch interceptor...")
        await buyin_page.evaluate("""
            window.__captured_apis = [];
            
            // Hook XMLHttpRequest
            const origOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, ...args) {
                this._capturedUrl = url;
                this._capturedMethod = method;
                this.addEventListener('load', function() {
                    if (this._capturedUrl && this.responseText) {
                        window.__captured_apis.push({
                            type: 'xhr',
                            method: this._capturedMethod,
                            url: this._capturedUrl,
                            status: this.status,
                            body: this.responseText.substring(0, 5000)
                        });
                    }
                });
                return origOpen.call(this, method, url, ...args);
            };
            
            // Hook fetch
            const origFetch = window.fetch;
            window.fetch = async function(...args) {
                const resp = await origFetch.apply(this, args);
                try {
                    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
                    const clone = resp.clone();
                    const text = await clone.text();
                    if (text && text.length > 50) {
                        window.__captured_apis.push({
                            type: 'fetch',
                            url: url,
                            status: resp.status,
                            body: text.substring(0, 5000)
                        });
                    }
                } catch(e) {}
                return resp;
            };
            
            console.log('XHR/Fetch interceptor installed');
        """)
        print("  Interceptor installed.")

        # Now navigate to the selection page to trigger API calls
        print("\n[Step 2] Navigate to selection square to trigger APIs...")
        await buyin_page.goto("https://buyin.jinritemai.com/dashboard/service/selection/square", wait_until="networkidle", timeout=60000)
        
        # Re-inject interceptor after navigation
        await buyin_page.evaluate("""
            window.__captured_apis = [];
            
            const origOpen2 = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, ...args) {
                this._capturedUrl = url;
                this._capturedMethod = method;
                this.addEventListener('load', function() {
                    if (this._capturedUrl && this.responseText) {
                        window.__captured_apis.push({
                            type: 'xhr',
                            method: this._capturedMethod,
                            url: this._capturedUrl,
                            status: this.status,
                            body: this.responseText.substring(0, 5000)
                        });
                    }
                });
                return origOpen2.call(this, method, url, ...args);
            };
            
            const origFetch2 = window.fetch;
            window.fetch = async function(...args) {
                const resp = await origFetch2.apply(this, args);
                try {
                    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
                    const clone = resp.clone();
                    const text = await clone.text();
                    if (text && text.length > 50) {
                        window.__captured_apis.push({
                            type: 'fetch',
                            url: url,
                            status: resp.status,
                            body: text.substring(0, 5000)
                        });
                    }
                } catch(e) {}
                return resp;
            };
        """)

        print("  Waiting for page to fully render (15s)...")
        await buyin_page.wait_for_timeout(15000)

        # Scroll multiple times
        print("  Scrolling to trigger lazy loading...")
        for i in range(5):
            await buyin_page.evaluate("window.scrollBy(0, 1000)")
            await buyin_page.wait_for_timeout(2000)

        # Collect captured APIs
        print("\n[Step 3] Collecting captured APIs...")
        captured = await buyin_page.evaluate("() => window.__captured_apis || []")
        print(f"  Captured {len(captured)} API calls")

        # Filter and display
        interesting = []
        for api in captured:
            url = api.get("url", "")
            body = api.get("body", "")
            if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".svg", ".woff", "monitor", "tcc?", "btm_mapping", "ab_param"]):
                continue
            if len(body) < 50:
                continue
            interesting.append(api)
            print(f"  [{api.get('type')}] {api.get('status')} {url[:120]}")
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    print(f"    code={data.get('code')} st={data.get('st')} keys={list(data.keys())[:8]}")
                    d = data.get("data")
                    if isinstance(d, dict):
                        print(f"    data.keys={list(d.keys())[:12]}")
                    elif isinstance(d, list) and d:
                        print(f"    data is list[{len(d)}], first keys={list(d[0].keys())[:10] if isinstance(d[0], dict) else 'N/A'}")
            except:
                pass

        # Save
        output_file = OUTPUT_DIR / "buyin_xhr_captured.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(interesting, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {output_file}")

        await browser.close()
    print(f"Total interesting APIs: {len(interesting)}")


if __name__ == "__main__":
    asyncio.run(hook_buyin_xhr())
