# One Mini — AI 电商选品平台

## 架构

```
┌──────────────────────────────────────────────────────────┐
│  前端 (Vue 3 + TailwindCSS)    port 80 (nginx)           │
│    → 任务看板 / 选品表单 / 产品网格 / ROI 图表           │
└────────────┬─────────────────────────────────┬───────────┘
             │ /api/*                          │ /ai/*
             ▼                                 ▼
┌────────────────────────┐     ┌────────────────────────────┐
│ 后端 (Spring Boot)     │     │ AI Engine (FastAPI)        │
│ port 8080 (Docker)     │────→│ port 8001 (宿主机)          │
│ JDK 17 + JPA + Redis   │     │ Python 3.12 + Playwright   │
└────────┬───────────────┘     └──────┬─────────────────────┘
         │                            │
    ┌────▼────┐              ┌────────▼────────┐
    │ MySQL   │              │ Redis Stream    │
    │ 8.0     │              │ agent:task      │
    │ (Docker)│              │ agent:result    │
    └─────────┘              └─────────────────┘
```

## 快速启动

### 本地开发（需要 Edge 浏览器 + 已登录蝉妈妈/巨量百应）

```bash
# 1. 启动基础设施
cd one_mini
docker compose up -d mysql redis backend frontend

# 2. 配置环境变量
cp ai-engine/.env.example ai-engine/.env
# 编辑 .env 填入 MINIMAX_API_KEY、CHANMAMA_COOKIE、BUYIN_COOKIE 等

# 3. 启动 AI Engine（需要 Edge 浏览器已关闭）
cd ai-engine
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 4. 打开前端
# http://localhost → 新建选品任务 → 输入关键词 → 开始分析
```

### 服务器部署（仅 Cookie 模式，无 Edge 依赖）

```bash
docker compose -f docker-compose.server.yml up -d
# Chanmama 用 Cookie 注入，1688/巨量百应 自动跳过
```

## AI Engine 内部结构

```
ai-engine/app/
├── agents/               智能体
│   ├── product_picker.py    选品：蝉妈妈 → 品名 → Buyin → LLM 筛选
│   ├── finance_analyst.py   财务：到手价 × 佣金率 → 净利 → ROI
│   └── base_agent.py        基类
├── spiders/              爬虫
│   ├── chanmama.py          蝉妈妈 SPUrank (API拦截, 25字段, ≤100条)
│   ├── buyin.py             巨量百应选品广场 (到手价/佣金/月销)
│   ├── yiwugo.py            义乌购 (Playwright headless)
│   ├── alibaba1688.py       1688 (persistent_context + captcha检测)
│   ├── wholesale_aggregator.py  批发聚合器
│   ├── cookie_manager.py    Cookie 管理
│   └── browser.py           CDP 浏览器管理（已停用）
├── llm/                  大语言模型
│   ├── minimax.py           主模型 MiniMax M2.7-highspeed
│   ├── doubao.py            备用: 豆包 Doubao
│   ├── deepseek.py          备用: DeepSeek V4
│   ├── router.py            模型路由
│   └── base.py              接口定义
├── export/               Excel 导出
│   └── excel.py             5 sheets: 任务信息/蝉妈妈/百应/选品/财务
├── logger.py             统一日志 (7文件轮转, 10MB×5)
├── message_bus.py        Redis Stream 封装 (cursor模式, 防丢消息)
├── config.py             环境检测 + 自动检测 Edge Profile
└── main.py               FastAPI入口 + 生命周期 + 自动任务链
```

## 数据流

```
前端 POST /api/tasks { keywords: [ "口红" ], limit: 5 }
  → 后端 TaskController → MySQL (task 表, status=pending)
  → Redis XADD agent:task { task_id, to_agent: "product_picker", payload }
  → AI Engine XREAD agent:task
  → ProductPicker.process()
        ├── Chanmama: persistent_context(Edge Profile)
        │     → g.page("SPUrank?keyword=口红") → 拦截 /v1/spu/search API
        │     → 50条 SPU(25字段)
        ├── 提取品名: ["花西子蜜粉", "完美日记唇釉", ...]
        ├── Buyin: persistent_context(Edge Profile)
        │     → g.page("选品广场") → g.type(品名) → g.press("Enter")
        │     → 到手价/佣金/月销
        └── LLM → JSON → 选品结果
  → FinanceAnalyst.process()
        └── LLM → 到手价 × 佣金率 = 净利 → ROI → 推荐/观望/不推荐
  → Redis XADD agent:result { task_id, result_json }
  → 后端 TaskResultConsumer XREADGROUP → MySQL UPDATE status=completed
  → 前端 GET /api/tasks/{id} → 显示结果
  → Excel 自动导出到 ai-engine/logs/
```

## 环境变量

| 变量 | 说明 | 如何获取 |
|---|---|---|
| `MINIMAX_API_KEY` | LLM API key | https://platform.minimaxi.com |
| `CHANMAMA_COOKIE` | 蝉妈妈登录态 | Edge F12 → Application → Cookies → 复制 |
| `BUYIN_COOKIE` | 巨量百应登录态 | 同上, jinritemai.com 域名 |
| `REDIS_HOST/PORT` | Redis 地址 | 默认 localhost:6380 |

## API 概览

| 端点 | 说明 |
|---|---|
| `POST /api/tasks` | 创建选品任务 |
| `GET /api/tasks` | 任务列表 |
| `GET /api/tasks/{id}` | 任务详情 |
| `GET /ai/health` | AI Engine 健康检查 |
| `POST /ai/test/chat` | 测试 LLM 调用 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3, TypeScript, Vite 5, TailwindCSS |
| 后端 | Spring Boot 3.2, JDK 17, JPA + Hibernate, Redis Stream |
| AI | Python 3.12, FastAPI, MiniMax M2.7-highspeed, Playwright |
| 基础设施 | Docker, MySQL 8.0, Redis 7, nginx |

## 已知限制

1. **1688/巨量百应** 需宿主机 Edge Profile (不能 Docker 化)
2. **persistent_context** 需独占 Edge Profile (不能和 CDP 共存)
3. **蝉妈妈免费版** 不返回价格/佣金数据
4. **单任务耗时 ~2-4分钟** (3次百应搜索 + LLM)
5. **Edge 必须关闭** 再运行 AI Engine

## 架构债务 / 已知问题

### 抖音操作：Node.js 与 Python 双实现
- `douyin-creator-tools/src/*.mjs` — Node.js CLI，npm scripts 完整，独立可运行
- `ai-engine/app/spiders/douyin_creator.py` — Python 重写，供 AI Engine Agent 调用
- 两套实现功能完全重叠，抖音页面改版需两边都改

### Skills 层与 Python Agent 未对接
- `skills/douyin-operator/SKILL.md` 定义了 OpenClaw skill 元数据
- `ai-engine/app/agents/douyin_operator.py` 独立实现，不引用 skill 定义
- OpenClaw 调度的是 skill，而 skill 无法调用 Python agent

### 1688 / Yiwugo / WholesaleAggregator 保留为 fallback
- `alibaba1688.py`、`yiwugo.py`、`wholesale_aggregator.py` 文件保留但不在主 pipeline 中
- `__init__.py` 已注释掉相关 export，如需启用取消注释即可
- 1688 需要 Slider 验证（人工介入），不适合自动化

## 常见问题

### Q: 任务一直显示"进行中"？
A: 检查 Edge 是否已完全关闭 → kill msedge.exe → 重试。如果仍然卡住, 可能是 Redis consumer group 丢失 → 重启 AI Engine 即可。

### Q: 蝉妈妈返回 0 条数据？
A: 检查 `CHANMAMA_COOKIE` 是否过期 → 从浏览器重新导出 → 更新 `.env`。

### Q: 百应搜索"网络不稳定"？
A: 使用 `persistent_context` 而非 cookie 注入。确保 Edge 关闭后再启动爬虫。

### Q: Excel 文件在哪里？
A: `ai-engine/logs/` 目录, 以 `product_picker_xxx_timestamp.xlsx` 命名。

## 开发指南

### 添加新爬虫

1. 在 `ai-engine/app/spiders/` 创建新 `.py` 文件
2. 实现 `search_products(keyword, limit)` 函数, 返回 `[{product_name, price, ...}]`
3. 在 `wholesale_aggregator.py` 中添加新平台
4. 在 `__init__.py` 中导出

### 添加新智能体

1. 在 `ai-engine/app/agents/` 创建新文件
2. 继承 `BaseAgent`, 实现 `process(task_id, payload)` 方法
3. 在 `main.py` lifespan 中注册 `agents["new_agent"] = NewAgent(bus)`
4. 在 `_consume_tasks()` 中添加路由逻辑
