# 网页数据采集工具 设计文档

## 概述

基于 AI Agent（DeepSeek + Playwright）的智能网页数据采集工具。用户输入 URL 和要提取的字段（自然语言描述），AI 自动理解页面内容并提取对应数据，保存到本地 JSON/CSV。

## 目标

- 2 天内出 MVP，可运行、可展示、可写简历
- AI 驱动解析页面结构变化，而非固定 CSS 选择器
- 零前端、命令行操作

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | Agent 全权编写 |
| 浏览器 | Playwright | MCP 已配置 |
| AI 解析 | DeepSeek API | 已有 API Key |
| 搜索增强 | Tavily (可选) | 已有 API Key，MVP 阶段暂不启用 |
| 存储 | JSON + CSV | 两种格式同时输出 |
| 依赖管理 | requirements.txt | pip install -r 一次性安装 |

## 架构

```
用户命令行输入
    ↓
cli.py ──解析参数──→ browser.py ──打开网页、获取文本──→ extractor.py ──DeepSeek提取字段──→ storage.py ──保存文件
                                                                                              ↓
                                                                                        output/ 目录
```

### 模块职责

**run.py** — 唯一入口
- 加载 `.env` 环境变量
- 解析 CLI 参数
- 编排各模块调用顺序

**scraper/cli.py** — 命令行参数解析
- `--url`：目标页面 URL（必填）
- `--fields`：要提取的字段，逗号分隔
- `--output`：可选，输出格式 `json` / `csv` / `both`（默认 both）
- 未来扩展：`--search` 用 Tavily 搜索后采集

**scraper/browser.py** — 浏览器控制
- 基于 Playwright 打开页面
- 等待页面完全加载（networkidle）
- 获取页面纯文本内容（标题 + body 文本）
- 自动清理过长的空白和噪音
- 关闭浏览器

**scraper/extractor.py** — AI 解析引擎 ★
- 构建 prompt：告诉 DeepSeek 页面文本 + 用户要提取的字段
- 调用 DeepSeek API 解析并返回结构化 JSON
- 失败重试 1 次
- Token 节省：页面过长时自动裁剪

**scraper/storage.py** — 数据持久化
- 自动创建 `output/` 目录
- 按时间戳生成子目录：`output/20250713_103000/`
- 同时保存 `data.json` 和 `data.csv`
- CSV 文件可直接用 Excel / WPS 打开

## 数据流

```
1. CLI 解析 → {url, fields, output_format}
2. Browser → 获取页面文本
3. Extractor → DeepSeek API → 结构化 JSON
4. Storage → 写 data.json + data.csv
5. 终端打印结果摘要
```

## 错误处理

- URL 不可达 → 提示检查 URL，退出
- DeepSeek API 异常 → 重试 1 次，失败后友好报错
- 字段提取不全 → 返回 null，不崩溃
- 输出目录写入失败 → 提示权限问题

## 项目结构

```
E:\web-scraper\
├── run.py                  ← 入口，只运行这一个文件
├── requirements.txt        ← 依赖清单
├── .env                    ← API Key 配置
├── .gitignore
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2025-07-13-web-scraper-design.md
├── scraper/
│   ├── __init__.py
│   ├── cli.py              ← 命令行参数
│   ├── browser.py          ← Playwright 控制
│   ├── extractor.py        ← DeepSeek 解析
│   └── storage.py          ← 数据保存
└── output/                 ← 结果目录（自动生成）
```

## 迭代计划

### MVP（Day 1-2）
- [x] 基础 CLI 参数解析
- [x] Playwright 单页文本获取
- [x] DeepSeek 字段提取
- [x] JSON + CSV 输出
- [ ] 用户验证 + 简历描述

### 扩展（Day 3+）
- [ ] Tavily 搜索 → 自动找页面
- [ ] 列表页批量采集
- [ ] 定时监控（配合竞品项目）
- [ ] 可视化界面
