# 选品分析智能体

## 描述
从抖音、蝉妈妈等平台抓取热销数据，使用 Doubao-Seed-2.0-pro 进行多模态趋势分析，输出潜力爆品清单。

## 工作流

### 1. 选品分析 (product_analysis)
**输入:**
```json
{
  "keywords": ["美妆", "护肤"],
  "platform": "douyin",
  "limit": 10
}
```

**输出:**
```json
{
  "products": [
    {
      "name": "商品名称",
      "category": "品类",
      "price_range": "建议定价范围",
      "target_audience": "目标客群",
      "potential_score": 8,
      "competition_level": "中",
      "supply_difficulty": "低",
      "roi_expectation": "预期ROI",
      "risk_notes": "风险提示",
      "promotion_suggestion": "推广建议"
    }
  ],
  "market_summary": "市场概况总结",
  "trend_analysis": "趋势分析"
}
```

### 2. 自动流转
选品分析完成后，自动触发财务审核流程。