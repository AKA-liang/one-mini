import json

with open(r"C:\liangtao\OpenCode\one_mini\ai-engine\spider_test\output\buyin_context_captured.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    url = item["url"]
    body = item["body"]
    if "channel_activity" in url:
        print("=== CHANNEL API ===")
        print("URL:", url[:200])
        d = json.loads(body)
        products = d.get("data", {}).get("data", [])
        print("Products count:", len(products))
        if products:
            for p in products[:2]:
                pmts = p.get("pmts", [])
                print("  pmts count:", len(pmts))
                for pm in pmts[:3]:
                    pid = pm.get("product_id", "")
                    price = pm.get("price", "")
                    cos = pm.get("cos_ratio", "")
                    fee = pm.get("cos_fee", "")
                    cover = pm.get("cover", "")[:80]
                    title = pm.get("title", pm.get("product_name", ""))
                    print(f"    pid={pid} price={price} cos_ratio={cos} cos_fee={fee} title={title[:50]} cover={cover}")

    elif "material_list" in url:
        d = json.loads(body)
        promos = d.get("data", {}).get("promotions", [])
        promos_pc = d.get("data", {}).get("promotions_pc")
        has_more = d.get("data", {}).get("has_more")
        extra = d.get("data", {}).get("extra", {})
        channel_id = extra.get("channel_id", "")
        recall = extra.get("recall_type", "")
        search_id = extra.get("search_id", "")[:40]
        print("=== MATERIAL_LIST ===")
        print(f"  promotions: {len(promos)}, promotions_pc type: {type(promos_pc).__name__}, has_more: {has_more}")
        print(f"  channel_id: {channel_id}, recall: {recall}, search_id: {search_id}...")
        if promos:
            for pm in promos[:2]:
                print(f"    promo: {json.dumps(pm, ensure_ascii=False)[:300]}")
        if promos_pc and isinstance(promos_pc, list) and promos_pc:
            for pm in promos_pc[:2]:
                print(f"    promo_pc: {json.dumps(pm, ensure_ascii=False)[:300]}")

    elif "filter_info" in url:
        d = json.loads(body)
        print("=== FILTER_INFO ===")
        print(f"  keys: {list(d.get('data', {}).keys())[:15]}")

    elif "cate_info" in url:
        d = json.loads(body)
        print("=== CATE_INFO ===")
        cates = d.get("data", {}).get("category_list", d.get("data", {}).get("cate_list", []))
        print(f"  categories: {len(cates) if isinstance(cates, list) else 'N/A'}")
        if isinstance(cates, list) and cates:
            for c in cates[:5]:
                print(f"    {c.get('name', c.get('cate_name', ''))}")

    elif "search/sug" in url:
        d = json.loads(body)
        print("=== SEARCH_SUG ===")
        print(f"  data: {json.dumps(d.get('data', {}), ensure_ascii=False)[:300]}")
