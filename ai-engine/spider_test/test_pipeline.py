"""
Chanmama + Buyin two-source pipeline.
  Stage 1: Chanmama SPUrank → hot products (25 fields)
  Stage 2: Buyin by name → price + commission + sales
  Stage 3: LLM selection + Finance analysis
"""
from __future__ import annotations

import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")


async def test():
    from app.spiders.chanmama import search_hot_products_persistent
    from app.spiders.buyin import search_buyin
    from app.agents.product_picker import PRODUCT_PICKER_PROMPT, ProductPickerAgent
    from app.agents.finance_analyst import FINANCE_ANALYST_PROMPT
    from app.llm.base import LLMMessage
    from app.llm.router import chat
    import re

    keyword = "手机壳"
    t0 = time.time()

    # Stage 1: Chanmama
    print("=" * 60)
    print("STAGE 1: Chanmama SPUrank")
    print("=" * 60)
    chanmama = await asyncio.to_thread(search_hot_products_persistent, keyword=keyword, limit=50)
    print(f"  Products: {len(chanmama)}")
    if chanmama:
        f = chanmama[0]
        print(f"  Sample: {f.get('title','?')[:30]} | creator={f.get('creator_count')} | sales_idx={f.get('sales_volume_index')}")

    # Extract names
    agent = ProductPickerAgent.__new__(ProductPickerAgent)
    names = agent._extract_product_names(chanmama, n=3)
    print(f"\n  Names for Buyin: {names}")

    # Stage 2: Buyin
    print("\n" + "=" * 60)
    print("STAGE 2: Buyin by name")
    print("=" * 60)
    all_buyin = []
    seen = set()
    for name in names[:3]:
        products = await asyncio.to_thread(search_buyin, keyword=name, limit=3)
        print(f"  '{name[:30]}' → {len(products)} results")
        for p in products:
            pn = p.get("product_name", "")
            if pn and pn not in seen:
                seen.add(pn)
                all_buyin.append(p)
                print(f"    {pn[:30]} | ¥{p.get('price')} | {p.get('commission_rate',0):.0%} | 月销{p.get('sales')}")
    print(f"\n  Total Buyin: {len(all_buyin)}")

    # Stage 3: LLM
    print("\n" + "=" * 60)
    print("STAGE 3: LLM pick + finance")
    print("=" * 60)

    ctx = (f"关键词：{keyword}\n需要推荐：5 款\n\n"
           f"## 蝉妈妈热销SPU\n{json.dumps(agent._simplify_chanmama(chanmama[:15]), ensure_ascii=False, indent=2)}\n\n"
           f"## 巨量百应选品广场（精确匹配）\n{json.dumps(all_buyin[:10], ensure_ascii=False, indent=2)}\n\n"
           f"请综合需求热度和实际采购价，选出最优5款商品。")

    resp = await chat("product_analysis", [
        LLMMessage(role="system", content=PRODUCT_PICKER_PROMPT),
        LLMMessage(role="user", content=ctx),
    ], temperature=0.7)

    picker = _parse_json(resp.content)
    products = picker.get("products", [])
    print(f"  Selected {len(products)} products:")
    for p in products[:5]:
        if p and isinstance(p, dict):
            print(f"    {p.get('name','?')[:30]} | ¥{p.get('price','?')} | 佣金{p.get('commission_rate','?')}")

    # Finance
    if products:
        print("\n  Finance analysis:")
        with_prices = []
        for p in products:
            name = p.get("name", "")
            price = p.get("price")
            if name and price is not None:
                with_prices.append({"name": name, "price": float(price),
                                     "commission_rate": p.get("commission_rate", 0),
                                     "monthly_sales": p.get("monthly_sales")})

        fin_ctx = (f"选品数据（含真实到手价+佣金率）：\n{json.dumps(with_prices, ensure_ascii=False, indent=2)}\n\n"
                   f"佣金收入 = price × commission_rate，净利润 = 佣金收入 - 物流(≥2元) - 广告(5%~10%)。")

        fin_resp = await chat("finance_review", [
            LLMMessage(role="system", content=FINANCE_ANALYST_PROMPT),
            LLMMessage(role="user", content=fin_ctx),
        ], temperature=0.3)

        fin = _parse_json(fin_resp.content)
        for fp in fin.get("products", [])[:5]:
            print(f"    {fp.get('name','?')[:20]}: 佣金¥{fp.get('commission_income',0)} | "
                  f"净利¥{fp.get('net_profit_per_order',0)} | {fp.get('recommendation','?')}")
        print(f"\n  {fin.get('overall_assessment','?')[:150]}")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"Pipeline: {elapsed:.0f}s")
    print(f"{'=' * 60}")

    # Export Excel
    from app.export.excel import export_task_data
    fp = export_task_data(
        task_id=f"test-{int(time.time())}", keywords=keyword,
        budget=None, category=None,
        chanmama_data=chanmama,
        buyin_data=all_buyin,
        llm_products=products,
        finance_data=fin.get("products", []) if products else None,
        agent="test_pipeline",
    )
    print(f"\nExcel saved: {fp}")


def _parse_json(content: str) -> dict:
    import re
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", content)
        if blocks:
            try:
                return json.loads(blocks[0].strip())
            except json.JSONDecodeError:
                pass
        brace = re.search(r"\{[\s\S]*\}", content)
        if brace:
            try:
                return json.loads(brace.group(0))
            except json.JSONDecodeError:
                pass
        return {}


asyncio.run(test())
