# AI 网页数据采集工具

基于 AI Agent（DeepSeek + Playwright）的智能网页数据采集工具。用户输入 URL 和自然语言字段描述，AI 自动理解页面内容并提取对应数据，保存到本地 JSON/CSV。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（复制 .env.example 为 .env，填入你的 DeepSeek API Key）

# 3. 运行
python run.py --url "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" --fields "书名,价格,库存,描述"
```

## 使用示例

```bash
# 抓取商品详情
python run.py --url "https://example.com/product/123" --fields "名称,价格,规格,库存"

# 指定输出格式（默认 JSON+CSV 都保存）
python run.py --url "https://example.com" --fields "标题,作者" --output json
```

## 输出

自动创建 `output/<时间戳>/` 目录，包含：
- `data.json` — 结构化数据（含元信息）
- `data.csv` — 可直接用 Excel/WPS 打开

## 技术栈

- **Python** — 核心语言
- **DeepSeek API** — AI 驱动的内容理解与字段提取
- **BeautifulSoup + requests** — 网页内容获取
- **Playwright**（可选）— JavaScript 渲染页面支持

## 架构

```
用户输入命令
    ↓
浏览器模块 → 获取页面文本
    ↓
AI提取模块 → DeepSeek 理解页面 → 按需提取字段
    ↓
存储模块 → 保存 JSON + CSV
```

## 简历描述

> **AI Agent 驱动的智能网页数据采集系统**
>
> 基于 DeepSeek 大语言模型和 Python 实现的智能数据采集工具，具备以下核心能力：
> - **AI 自适应解析**：不依赖固定 CSS 选择器，通过 LLM 理解页面语义，自动适应页面结构变化
> - **自然语言字段定义**：用户用中文描述要采集的字段（如"书名、价格"），系统自动匹配提取
> - **多格式输出**：同时输出 JSON 和 CSV 格式，CSV 可直接在 Excel/WPS 中打开
> - **模块化架构**：CLI 解析 → 页面获取 → AI 提取 → 数据存储，每层职责清晰

## TODO / 扩展计划

- [ ] Tavily 搜索增强（输入关键词自动搜索→采集）
- [ ] 列表页批量采集
- [ ] 定时监控（配合竞品价格监控项目）
- [ ] Web 可视化界面
