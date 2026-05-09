import json

with open(r"C:\liangtao\OpenCode\one_mini\ai-engine\spider_test\output\buyin_search_all_apis.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    url = item["url"]
    body_len = item["body_len"]
    if "material_list" in url and body_len > 10000:
        print(f"=== MATERIAL_LIST ({body_len} bytes) ===")
        print(f"URL: {url[:200]}")
        body = item["body"]
        try:
            d = json.loads(body)
            data_inner = d.get("data", {})
            promos = data_inner.get("promotions", [])
            promos_pc = data_inner.get("promotions_pc")
            has_more = data_inner.get("has_more")
            extra = data_inner.get("extra", {})
            channel_id = extra.get("channel_id", "")
            recall_type = extra.get("recall_type", "")
            search_id = extra.get("search_id", "")[:40]

            print(f"  promotions: {len(promos)}, has_more: {has_more}")
            print(f"  channel_id: {channel_id}, recall_type: {recall_type}")
            print(f"  promotions_pc type: {type(promos_pc).__name__}")

            if promos:
                print(f"\n  --- First 3 promotions ---")
                for i, pm in enumerate(promos[:3]):
                    print(f"\n  Product {i+1}:")
                    for k, v in pm.items():
                        vstr = str(v)
                        if len(vstr) > 200:
                            print(f"    {k}: {vstr[:200]}...")
                        else:
                            print(f"    {k}: {vstr}")

            if isinstance(promos_pc, dict):
                print(f"\n  promotions_pc keys: {list(promos_pc.keys())[:10]}")
                pc_list = promos_pc.get("list", promos_pc.get("items", []))
                if isinstance(pc_list, list) and pc_list:
                    print(f"  promotions_pc.list: {len(pc_list)} items")
                    for i, pm in enumerate(pc_list[:2]):
                        print(f"\n  PC Product {i+1}:")
                        for k, v in pm.items():
                            vstr = str(v)
                            if len(vstr) > 200:
                                print(f"    {k}: {vstr[:200]}...")
                            else:
                                print(f"    {k}: {vstr}")
            elif isinstance(promos_pc, list) and promos_pc:
                print(f"\n  promotions_pc: {len(promos_pc)} items")
                for i, pm in enumerate(promos_pc[:2]):
                    print(f"\n  PC Product {i+1}:")
                    for k, v in pm.items():
                        vstr = str(v)
                        if len(vstr) > 200:
                            print(f"    {k}: {vstr[:200]}...")
                        else:
                            print(f"    {k}: {vstr}")

            # Save the full parsed data
            output = f"buyin_parsed_material_{body_len}.json"
            with open(rf"C:\liangtao\OpenCode\one_mini\ai-engine\spider_test\output\{output}", "w", encoding="utf-8") as f2:
                json.dump(d, f2, ensure_ascii=False, indent=2)
            print(f"\n  Saved parsed to: {output}")

        except json.JSONDecodeError:
            print("  JSON parse error (truncated)")
            # Try to find promotions in partial body
            idx = body.find('"promotions"')
            if idx > 0:
                print(f"  Found 'promotions' at index {idx}")
