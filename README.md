# AI 网页数据采集工具

> **用自然语言描述要什么，AI 自动理解页面并提取数据**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-green)](https://deepseek.com)

## 核心亮点

| 特性 | 说明 |
|------|------|
| AI 自适应解析 | 不用CSS选择器，DeepSeek AI 自动理解页面语义 |
| 自然语言字段 | 输入"书名、价格、出版社"，AI 自己去页面里找 |
| 批量采集 | 输入搜索列表页，自动识别所有商品链接，逐个提取 |
| 双格式输出 | JSON + CSV，CSV 可直接 Excel 打开 |
| 登录模式 | 支持手动登录淘宝/京东，保存 Session 后采集 |
| Web 界面 | 浏览器打开即可操作，无需命令行 |

## 快速开始

### 安装

```bash
git clone https://github.com/1161135/web-scraper-tool.git
cd web-scraper-tool
pip install -r requirements.txt
cp .env.example .env   # 填入你的 DeepSeek API Key
```

### 运行

```bash
# 单页模式
python run.py --url "https://product.dangdang.com/29311943.html" --fields "Title, Author, Price, Publisher"

# 列表批量模式
python run.py --url "http://search.dangdang.com/?key=活着" --fields "Title, Author, Price" --auto --limit 20
```

### Web 界面

```bash
python app.py
# 浏览器打开 http://127.0.0.1:5000
```

## 使用示例

### 单品采集

```bash
python run.py --url "https://product.dangdang.com/29311943.html" --fields "Title, Author, Price, Publisher"
```

输出：
```
Title:    活着（余华代表作，精装，易烊千玺推荐阅读）
Author:   余华
Price:    ¥31.00
Publisher: 北京十月文艺出版社
```

### 列表批量采集

```bash
python run.py --url "http://search.dangdang.com/?key=活着" --fields "Title, Author, Price" --auto --limit 10
```

输出：自动找到 10 个商品 → 逐个提取 → 汇总成表格（JSON+CSV+HTML）

### 登录采集（淘宝/京东）

```bash
python run.py --login    # 打开浏览器手动登录，保存 Session
python run.py --url "https://item.taobao.com/item.htm?id=XXX" --fields "商品名称,价格,销量"
```

## 项目结构

```
web-scraper-tool/
├── run.py               # 命令行入口
├── app.py               # Web 界面入口
├── templates/           # Web 页面模板
├── scraper/
│   ├── cli.py           # 命令行参数
│   ├── browser.py       # 页面内容获取 (Playwright + requests)
│   ├── extractor.py     # DeepSeek AI 提取引擎
│   ├── scout.py         # 列表页自动识别商品链接
│   ├── storage.py       # JSON/CSV 存储
│   ├── reporter.py      # HTML 报告生成
│   └── login.py         # 登录 Session 管理
└── output/              # 采集结果
```

## 技术栈

| 技术 | 用途 |
|------|------|
| Python | 核心语言 |
| DeepSeek API | AI 内容理解与字段提取 |
| Playwright | 浏览器自动化（JS渲染页面） |
| BeautifulSoup | HTML 解析 |
| Flask | Web 界面 |

## 简历描述

> **AI Agent 驱动的智能网页数据采集系统**
>
> 基于 DeepSeek 大语言模型实现的智能数据采集工具，用户用**自然语言描述字段**，AI 自动理解页面语义并提取对应数据。支持单页采集与列表页批量采集，自动输出 JSON/CSV/HTML 报告。集成 Playwright 浏览器自动化，支持登录 Session 持久化，可采集需要登录的平台。
>
> **技术栈：** Python · DeepSeek API · Playwright · BeautifulSoup · Flask

## 项目地址

https://github.com/1161135/web-scraper-tool
