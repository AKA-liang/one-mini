# 抖音运营智能体

## 描述
基于 douyin-creator-tools 的抖音自动化能力，实现评论管理、自动回复、内容发布和数据导出。

## 依赖
- douyin-creator-tools 项目
- Playwright 持久化浏览器会话
- SQLite 评论数据库

## 工作流

### 1. 列出作品 (list_works)
列出抖音创作者中心的所有作品。

### 2. 导出未回复评论 (export_unreplied_comments)
导出指定作品中所有未回复的评论，供客服 Agent 分析和生成回复。

### 3. 批量回复评论 (reply_comments)
根据 AI 生成的回复计划，自动在抖音创作者中心批量回复评论。

### 4. 发布文章 (publish_article)
在抖音创作者中心发布图文内容。

### 5. 发布图文 (publish_imagetext)
在抖音创作者中心发布多图内容。

## 约束
- 评论回复不超过 400 Unicode 字符
- 使用中文引号
- 不修改 `status` 和 `appliedReplyMessage` 字段
- 不要绕过登录验证，由用户手动扫码登录
- 不要清除 `.playwright/douyin-profile` 目录