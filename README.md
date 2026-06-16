# AI 网页数据采集工具

> 输入网址，用自然语言描述字段，AI 自动提取数据。支持单品采集与列表页批量采集。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-green)](https://deepseek.com)

---

## 快速上手

### 安装

```bash
git clone https://github.com/1161135/web-scraper-tool.git
cd web-scraper-tool
pip install -r requirements.txt
cp .env.example .env   # 填入你的 DeepSeek API Key
```

### 单品采集

```bash
python run.py \
  --url "https://product.dangdang.com/29311943.html" \
  --fields "Title, Author, Price, Publisher"
```

输出：
```
Title:    活着（余华代表作，精装，易烊千玺推荐阅读）
Author:   余华
Price:    ¥31.00
Publisher: 北京十月文艺出版社
```

### 列表批量采集

自动识别搜索页中的所有商品链接，逐个提取数据：

```bash
python run.py \
  --url "http://search.dangdang.com/?key=活着" \
  --fields "Title, Author, Price" \
  --auto --limit 20
```

### Web 界面

```bash
python app.py
# 浏览器打开 http://127.0.0.1:5000
```

---

## 核心功能

| 功能 | 说明 |
|------|------|
| AI 字段提取 | 用自然语言描述字段，DeepSeek 自动理解页面并提取 |
| 批量采集 | 输入搜索/列表页，自动识别商品链接，逐个提取汇总 |
| 双格式输出 | JSON + CSV，CSV 可直接用 Excel 打开 |
| 可视化报告 | 采集完自动生成 HTML 报告，浏览器打开即可查看 |
| 登录 Session | CLI 支持登录淘宝/京东，保存登录态后采集（`python run.py --login`） |

## 项目结构

```
web-scraper-tool/
├── run.py               # 命令行入口
├── app.py               # Web 界面入口
├── templates/           # Web 页面模板
├── scraper/
│   ├── cli.py           # 命令行参数
│   ├── browser.py       # 页面内容获取（Playwright + requests）
│   ├── extractor.py     # DeepSeek AI 提取引擎
│   ├── scout.py         # 列表页自动识别商品链接
│   ├── storage.py       # JSON/CSV 存储
│   ├── reporter.py      # HTML 报告生成
│   └── login.py         # 登录 Session 管理（CLI 专用）
└── output/              # 采集结果
```

## 技术栈

Python · DeepSeek API · Playwright · BeautifulSoup · Flask

## 项目地址

https://github.com/1161135/web-scraper-tool
