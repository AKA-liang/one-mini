import json

with open(r"C:\liangtao\OpenCode\one_mini\ai-engine\spider_test\output\buyin_detail_apis.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    url = item["url"]
    body = item["body"]
    # Find APIs with product data
    body_lower = body.lower()
    if any(kw in body_lower for kw in ["title", "product_name", "goods_name", "commission", "cos_ratio"]):
        if len(body) > 500:
            print(f"URL: {url[:150]}")
            print(f"Body len: {len(body)}")
            try:
                d = json.loads(body)
                print(f"Keys: {list(d.keys())[:10]}")
                dd = d.get("data", {})
                if isinstance(dd, dict):
                    print(f"data keys: {list(dd.keys())[:15]}")
                    for k, v in dd.items():
                        vstr = str(v)
                        if len(vstr) < 200:
                            print(f"  {k}: {vstr}")
                        elif any(nk in k.lower() for nk in ["title", "name", "product", "goods"]):
                            print(f"  {k}: {vstr[:150]}")
                elif isinstance(dd, list) and dd:
                    print(f"data: list[{len(dd)}]")
                    print(f"  first: {json.dumps(dd[0], ensure_ascii=False)[:300]}")
            except:
                pass
            print()
