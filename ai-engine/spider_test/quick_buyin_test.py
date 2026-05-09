"""Quick test: Buyin search with evaluate-based input"""
import sys, os, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, '.')
from app.spiders.buyin import search_buyin

r = search_buyin('奥菲顿线条花边KT糯米壳', limit=3)
print(f'Results: {len(r)}')
for p in r:
    print(f"  {p.get('product_name','')[:30]} | price={p.get('price')} | comm={p.get('commission_rate')} | sales={p.get('sales')}")
