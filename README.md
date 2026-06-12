# 🕷️ AI Agent 智能网页数据采集工具

> **用自然语言描述要什么，AI 自动理解页面并提取数据**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-green)](https://deepseek.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## ✨ 核心亮点

| 特性 | 说明 |
|------|------|
| 🧠 **AI 自适应解析** | 不用CSS选择器、不用XPath，DeepSeek AI 自动理解页面语义 |
| 🗣️ **自然语言字段** | 输入"书名、价格、库存"，AI 自己去页面里找 |
| 📁 **双格式输出** | 同时输出 JSON + CSV，CSV 可直接 Excel 打开 |
| 🚀 **零配置运行** | `pip install` → `python run.py`，两行命令跑通 |
| 🔄 **自动适应变化** | 网站改版了也不怕，AI 理解内容而非固定选择器 |

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- DeepSeek API Key（[免费注册](https://platform.deepseek.com)）

### 安装

```bash
# 1. 下载项目
git clone https://github.com/1161135/web-scraper-tool.git
cd web-scraper-tool

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env    # 然后把你的 Key 填入 .env
```

### 运行

```bash
# 抓取商品详情
python run.py \
  --url "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" \
  --fields "书名,价格,库存状态,描述"
```

**输出：**

```json
{
  "书名": "A Light in the Attic",
  "价格": "£51.77",
  "库存状态": "In stock (22 available)",
  "描述": "It's hard to imagine a world without..."
}
```

---

## 📖 使用示例

### 单商品采集

```bash
python run.py \
  --url "https://books.toscrape.com/catalogue/sapiens_996/index.html" \
  --fields "书名,价格,评价"
```

### 指定输出格式

```bash
# 只要 JSON
python run.py --url "..." --fields "标题,作者" --output json

# 只要 CSV（方便 Excel 打开）
python run.py --url "..." --fields "名称,价格" --output csv
```

---

## 🏗️ 项目结构

```
web-scraper-tool/
├── run.py                  ← 🚀 唯一入口
├── requirements.txt        ← 依赖清单
├── .env                    ← API Key（已 gitignore）
├── scraper/
│   ├── cli.py              ← 命令行参数解析
│   ├── browser.py          ← 页面内容获取
│   ├── extractor.py        ← 🤖 DeepSeek AI 提取引擎
│   └── storage.py          ← JSON / CSV 存储
└── output/                 ← 采集结果目录（自动生成）
```

## ⚙️ 架构流程

```
你的输入 ──→  CLI解析参数
                  ↓
           Browser获取页面文本
                  ↓
           DeepSeek AI理解内容
                  ↓
           按字段提取结构化数据
                  ↓
           保存 JSON + CSV ✅
```

**与传统爬虫的核心区别：**

| 传统爬虫 | 本工具 |
|----------|--------|
| 写 CSS 选择器 / XPath | 🙅 不需要，AI 理解内容 |
| 网站改版就得改代码 | ✅ 自动适应，AI 找数据 |
| 不同网站不同脚本 | ✅ 同一套工具通吃 |
| 需要懂 HTML/CSS | ✅ 说中文就行 |

---

## 📋 简历描述

> ### AI Agent 驱动的智能网页数据采集系统
>
> **技术栈：** Python · DeepSeek API · BeautifulSoup · Playwright
>
> - 基于大语言模型(DeepSeek)实现智能数据提取，用户用**自然语言描述字段**，AI 自动理解页面语义并提取对应数据
> - 采用 **AI 自适应解析策略**，不依赖固定CSS选择器，网站结构变化时无需修改代码
> - 支持 **JSON/CSV 双格式输出**，CSV 可直接在 Excel 中打开分析
> - 模块化架构设计（CLI→浏览器→AI提取→存储），每层职责清晰，便于扩展
> - 将传统RPA自动化升级为 **AI Agent 智能体方案**，显著降低维护成本

---

## 🔧 技术栈

| 技术 | 用途 |
|------|------|
| Python | 核心开发语言 |
| DeepSeek API | AI 内容理解与字段提取 |
| BeautifulSoup | HTML 解析与文本提取 |
| Playwright | 动态页面渲染支持（可选） |
| python-dotenv | 环境变量管理 |

---

## 🗺️ 开发路线

- [x] **MVP** — 单品详情页采集，AI 字段提取，JSON/CSV 输出
- [ ] **Tavily 搜索** — 输入关键词自动搜索目标页面
- [ ] **批量采集** — 列表页自动遍历所有条目
- [ ] **定时监控** — 定期检测价格/库存变化
- [ ] **Web 界面** — 图形化操作面板

---

## 📄 许可证

MIT License © 2025

---

> **💡 一个项目，展示三种能力：** AI Agent 开发 · 自动化采集 · 全栈工程思维
