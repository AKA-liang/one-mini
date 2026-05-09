# 本地爬虫测试

此目录用于在本地电脑（非云端）运行爬虫探索和测试脚本。

## 环境要求

- Python 3.12+（推荐Anaconda）
- Playwright: `pip install playwright && playwright install`
- 已登录目标网站的Edge浏览器Profile

## 测试脚本

### 巨量百应选品探索
```bash
python test_juliangbaiying.py
```
- 自动加载Edge Profile（复用已登录cookie）
- 访问巨量百应选品广场
- 捕获API响应并保存到 `output/` 目录
- **前提**：已在Edge Profile 1中登录巨量百应团长号

### 1688插件CSV导出
```bash
python test_1688_plugin.py
```
- 加载Edge Profile + 1688采购助手插件
- 检查插件在1688搜索页上的UI元素
- 分析插件通信机制
- **前提**：已安装1688采购助手插件

## 输出

所有输出保存在 `output/` 子目录：
- `buyin_*_api.json` - 巨量百应API响应
- `1688_plugin.png/html` - 1688页面截图和HTML
- `buyin_selection.png/html` - 巨量百应页面截图和HTML

## 数据源架构

```
选品Agent (product_picker)
├── 需求侧（前端数据）
│   ├── 蝉妈妈 ✅ 稳定（抖音热销/SPU排名）
│   └── 巨量百应 🔧 待接入（精选联盟选品库，团长号）
└── 供给侧（后端数据）
    ├── 义乌购 ✅ 稳定（批发价格/供应量）
    └── 1688 🔧 待接入（插件CSV方案）
```
