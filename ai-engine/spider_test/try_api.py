"""Try Chanmama product APIs with headers extracted from browser cookies."""
import sys, os, json, urllib.request
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, r'C:\liangtao\OpenCode\one_mini\ai-engine')
from app.config import settings

cookie = settings.chanmama_cookie
token = ''
for p in cookie.split("; "):
    if p.startswith("Authorization-By-CAS="):
        token = p.split("=", 1)[1]
        break

urls = [
    "/v1/product/new/rankList?keyword=%E6%89%8B%E6%9C%BA%E5%A3%B3&category_id=-1&page=1&size=5&sort=sale&date_type=day",
    "/v1/product/new/rankList?keyword=%E6%89%8B%E6%9C%BA%E5%A3%B3&category_id=-1&page=1&size=5",
]

base = "https://api-service.chanmama.com"

for path in urls:
    url = f"{base}{path}"
    req = urllib.request.Request(url)
    req.add_header("Cookie", cookie)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    req.add_header("Referer", "https://www.chanmama.com/promotionRank/")
    try:
        r = urllib.request.urlopen(req, timeout=15)
        data = json.loads(r.read().decode())
        if isinstance(data, list):
            items = data
        else:
            items = data.get("data", {}).get("list", data.get("data", []))
            if not items and isinstance(data.get("data"), list):
                items = data.get("data")
        print(f"API: {path}")
        print(f"  Items: {len(items)}")
        if items and isinstance(items, list) and len(items) > 0:
            first = items[0]
            print(f"  Keys: {list(first.keys())[:20]}")
            print(f"  Sample: {json.dumps(first, ensure_ascii=False)[:800]}")
        else:
            print(f"  Data keys: {list(data.keys())}")
            print(f"  Full: {json.dumps(data, ensure_ascii=False)[:500]}")
        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()
