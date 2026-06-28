# AI 网页数据采集 + 电商竞品价格监控

> 一套工具，两大核心功能：**AI 智能采集** + **定时价格监控**，二者无缝联动。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-green)](https://deepseek.com)
[![APScheduler](https://img.shields.io/badge/Schedule-APScheduler-orange)](https://apscheduler.readthedocs.io/)

---

## 🚀 功能概览

### 🔍 AI 网页数据采集工具
输入网址，用自然语言描述字段，DeepSeek AI 自动理解页面并提取数据。

| 功能 | 说明 |
|------|------|
| 单品采集 | 输入商品详情页 URL，提取指定字段 |
| 列表批量采集 | 输入搜索/列表页，自动识别商品链接，逐个提取汇总 |
| 双格式输出 | JSON + CSV，CSV 可直接用 Excel 打开 |
| 可视化报告 | 采集完自动生成 HTML 报告 |
| 登录 Session | 支持淘宝/京东登录态保存 |

### 📊 电商竞品价格监控
基于上述采集能力扩展的定时价格监控系统，自动追踪竞品价格变化。

| 功能 | 说明 |
|------|------|
| ⏰ 定时采集 | 每个商品独立配置采集间隔（默认 6 小时），APScheduler 后台自动运行 |
| 📈 价格变化检测 | 自动计算涨跌幅，超阈值触发告警（支持百分比和绝对值阈值） |
| 🔔 多渠道告警 | Web 页面告警列表 + 控制台 + 可选邮件/Webhook |
| 📉 价格趋势图 | Chart.js 可视化历史价格走势 |
| 🎯 监控看板 | Web 图形化管理，总览/详情/告警一目了然 |
| 🚫 智能去重 | 添加监控时自动检测重复 URL |
| 📤 导入导出 | 支持 JSON 配置文件的批量导入/导出 |

### 🔗 双向联动

```
采集商品 → 一键「加入价格监控」 → 自动定时追踪价格
     ↑                                    |
     └──────── 查看监控详情 ←──────────────┘
```

- **采集 → 监控**：采集完商品后，点击「📊 加入价格监控」按钮，自动填入商品信息到监控配置
- **监控 → 采集**：监控看板可直接跳转回采集工具继续探索同类商品

---

## 快速开始

### 安装

```bash
git clone https://github.com/1161135/web-scraper-tool.git
cd web-scraper-tool
pip install -r requirements.txt
cp .env.example .env   # 填入你的 DeepSeek API Key
```

### 启动 Web 界面

```bash
python app.py
# 浏览器打开 http://127.0.0.1:5000/
```

### 单品采集

```bash
python run.py \
  --url "https://product.dangdang.com/29311943.html" \
  --fields "Title, Author, Price, Publisher"
```

### 列表批量采集

```bash
python run.py \
  --url "http://search.dangdang.com/?key=活着" \
  --fields "Title, Author, Price" \
  --auto --limit 20
```

### 价格监控 CLI

```bash
# 添加监控目标
python run.py monitor add --name "商品名" --url "https://..." --fields "标题,价格" --price-field "价格"

# 查看监控列表
python run.py monitor list

# 手动采集一次
python run.py monitor run <目标ID>

# 启动后台调度器（持续运行）
python run.py monitor start

# 查看告警
python run.py monitor alerts

# 导入/导出配置
python run.py monitor export
python run.py monitor import monitor-targets.json
```

### 价格监控 Web 看板

启动 `python app.py` 后访问 **http://127.0.0.1:5000/monitor/**

- 📊 **总览** — 所有监控目标状态卡片
- 🎯 **监控目标** — 添加/编辑/删除/立即采集
- 🔔 **告警列表** — 价格异常通知（降价/涨价/阈值）

---

## 项目结构

```
web-scraper-tool/
├── app.py                 # Web 入口（采集 + 监控看板）
├── run.py                 # CLI 入口（采集 + monitor 子命令）
├── scraper/               # 🔍 数据采集核心
│   ├── browser.py         # 页面获取（Playwright + requests）
│   ├── extractor.py       # DeepSeek AI 字段提取
│   ├── scout.py           # 列表页自动识别商品链接
│   ├── storage.py         # JSON/CSV 存储
│   ├── reporter.py        # HTML 报告
│   ├── login.py           # 登录 Session 管理
│   ├── stealth_browser.py # 隐身浏览器（反检测）
│   └── dangdang_price.py  # 当当专用价格提取器
├── pricemon/              # 📊 价格监控模块
│   ├── db.py              # SQLite 数据层（targets/history/alerts）
│   ├── scheduler.py       # APScheduler 定时调度
│   ├── tracker.py         # 价格追踪 + 变化检测
│   ├── alerts.py          # 告警引擎（控制台/邮件/Webhook）
│   ├── blueprint.py       # Flask Web 路由
│   └── templates/         # 监控看板页面（6个）
├── templates/             # 采集页面模板
└── output/                # 采集结果输出
```

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 运行环境 |
| Flask | Web 框架 |
| DeepSeek API | AI 字段提取 |
| Playwright | 浏览器自动化（处理 JS 渲染页面） |
| APScheduler | 定时任务调度 |
| SQLite | 价格数据持久化 |
| Chart.js | 价格趋势可视化 |
| BeautifulSoup | HTML 解析 |

## 仓库地址

https://github.com/1161135/web-scraper-tool
