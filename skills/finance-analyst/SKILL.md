# 财务审核智能体

## 描述
基于选品结果，使用 DeepSeek-V4-pro 进行深度 ROI 推理分析，结合规则引擎进行常识校验，输出盈利预测和投资建议。

## 工作流

### 1. 财务审核 (finance_review)
**输入:**
```json
{
  "product_analysis": { ... },
  "original_task_id": "uuid"
}
```

**输出:**
```json
{
  "products": [
    {
      "name": "商品名称",
      "purchase_cost": 采购成本,
      "selling_price": 建议售价,
      "platform_commission": 平台佣金,
      "logistics_cost": 物流成本,
      "net_profit_per_order": 单均净利润,
      "profit_margin": 利润率,
      "roi": 预期ROI,
      "recommendation": "推荐/观望/不推荐",
      "risk_notes": "风险提示"
    }
  ],
  "overall_assessment": "整体评估",
  "investment_suggestion": "投资建议"
}
```

## 常识校验规则
- 平台佣金率: 5%-15%
- 物流成本: 不低于2元/单
- 退货率: 不超过30%
- 利润率: 不超过90%