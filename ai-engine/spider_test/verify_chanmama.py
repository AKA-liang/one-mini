"""Chanmama standalone verification"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.spiders.chanmama import search_hot_products_persistent

r = search_hot_products_persistent('口红', limit=5)
print(f'Results: {len(r)}')

if r:
    first = r[0]
    print('Fields:', list(first.keys())[:10])
    for p in r[:3]:
        title = p.get('title', '')[:50]
        brand = p.get('brand', '')
        sales_idx = p.get('sales_volume_index', 0)
        creator = p.get('creator_count', 0)
        shop = p.get('shop_count', 0)
        print(f'  title={title}')
        print(f'    brand={brand} sales_idx={sales_idx} creator={creator} shop={shop}')

    beauty_kw = ['口红','唇','唇膏','唇彩','唇釉','唇部','妆','美','粉','液','笔']
    matched = sum(1 for p in r if any(kw in p.get('title','') for kw in beauty_kw))
    pct = matched * 100 // len(r) if r else 0
    print(f'Relevance: {matched}/{len(r)} ({pct}%)')
    if pct >= 30:
        print('PASS: Chanmama is working correctly')
    else:
        print('WARN: Low relevance — search may not be filtering correctly')
else:
    print('FAIL: 0 results')
