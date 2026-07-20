# Index-extraction

> 基于 XPath 行列交叉定位的网页表格 RPA 数据提取、桌面悬浮实时展示工具

## 项目简介

Index-extraction 是一款桌面端网页 RPA 自动化数据提取工具。核心基于 **手写行列交叉 XPath** 精准抓取 DIV 结构网页表格数据，搭配 **PyQt6 桌面悬浮窗** 实时展示抓取结果。采用前后端分离架构，后端通过 Selenium + Chrome 驱动静默抓取，前端 Vue3 提供完整的数据管理面板，适配 Vue 动态渲染网页。

### 核心特性

- 🔍 **行列交叉 XPath**：手写 XPath 规则，基于行（row）列（col）交叉定位，精准提取表格单元格
- 🪟 **桌面悬浮窗**：PyQt6 置顶悬浮窗实时展示提取数据，无需切换窗口
- 🌐 **动态渲染适配**：专为 DIV 结构表格和 Vue 动态渲染 DOM 设计
- 📡 **SSE 实时推送**：Server-Sent Events 实时推送抓取数据到前端和悬浮窗
- 🔌 **插拔式架构**：RPA 抓取、浏览器驱动、XPath 规则、数据解析完全解耦

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Vue3 + Vite + TailwindCSS + shadcn-vue | 组合式 API `<script setup>` |
| **前端路由** | VueRouter4 | SPA 路由管理 |
| **前端状态** | Pinia | 全局状态管理 |
| **前端图标** | Lucide | 图标库 |
| **HTTP 客户端** | Axios | 接口请求 + SSE 数据流 |
| **后端** | Python + FastAPI + Uvicorn | RESTful API + SSE |
| **数据校验** | Pydantic v2 | 请求/响应模型 |
| **RPA 引擎** | Selenium + webdriver-manager | Chrome 自动化驱动 |
| **桌面悬浮窗** | PyQt6 | 置顶悬浮窗口 |
| **打包** | Nuitka（后端）+ Vite（前端） | 独立可分发的桌面程序 |
| **环境管理** | python-dotenv | .env 多环境配置 |
| **日志** | loguru | 前后端统一日志 |
| **数据存储** | 本地 JSON（初期）| 预留 SQLite 迁移接口 |

### 强制配套技术

- python-dotenv：区分 `.env.development`、`.env.production` 两套配置
- loguru：统一日志格式，记录抓取失败、浏览器异常、接口报错
- 本地 JSON 文件：初期缓存抓取数据，无缝预留 SQLite 迁移接口
- Chrome 自动化驱动：后台静默运行
- Nuitka：打包独立桌面程序
- FastAPI auto docs：接口文档，严格 Restful 风格

---

## 环境配置说明

1. 复制配置模板：`cp .env.example .env.development`
2. 按需修改对应环境变量
3. 开发环境：`APP_ENV=development`（浏览器可见、日志全开）
4. 生产环境：`APP_ENV=production`（浏览器静默、精简日志）

| 配置文件 | 用途 | Git |
|----------|------|-----|
| `.env.example` | 通用模板，含所有注释 | ✅ 提交 |
| `.env.development` | 本地开发配置 | ❌ 忽略 |
| `.env.production` | 打包生产配置 | ❌ 忽略 |

---

## 本地开发 & 运行步骤

### 前置要求

- Node.js >= 18
- Python >= 3.10
- Chrome 浏览器

### 后端启动

```bash
cd backend
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 桌面悬浮窗启动

```bash
cd desktop
python main.py
```

---

## 项目目录结构

```
Index-extraction/
├── frontend/                    # Vue3 前端项目
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/              # shadcn-vue UI 组件
│   │   │   └── common/          # 公共业务组件
│   │   ├── pages/               # 页面容器组件
│   │   ├── router/              # VueRouter 路由配置
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── utils/               # 前端工具函数
│   │   ├── assets/              # 静态资源
│   │   └── layouts/             # 布局组件
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── package.json
│   └── package-lock.json
├── backend/                     # FastAPI 后端 + 核心 RPA 业务
│   ├── api/                     # 接口路由
│   ├── core/                    # 核心配置（FastAPI 实例、中间件）
│   ├── models/                  # Pydantic 数据模型
│   ├── services/                # 业务服务层
│   │   ├── rpa/                 # RPA 抓取业务
│   │   └── browser/             # 浏览器驱动服务
│   ├── utils/                   # 后端工具函数
│   ├── app.py                   # FastAPI 入口
│   └── requirements.txt         # Python 依赖
├── desktop/                     # PyQt6 桌面悬浮窗
│   ├── components/              # 悬浮窗 UI 组件
│   ├── utils/                   # 桌面端工具
│   └── main.py                  # 悬浮窗入口
├── config/                      # 全局配置
│   ├── xpath_rules.json         # XPath 抓取规则
│   ├── log_config.json          # 日志配置
│   └── settings.py              # 全局配置加载器
├── static/                      # 静态资源
│   └── cache/                   # 数据缓存
├── docs/                        # 项目文档
├── utils/                       # 公共工具类
│   ├── browser_utils.py         # 浏览器工具
│   ├── xpath_utils.py           # XPath 工具
│   └── log_utils.py             # 日志工具
├── .env.example                 # 环境变量模板
├── .gitignore
└── README.md
```

---

## 统一开发规范

### 前端规范
- 统一使用 `<script setup>` 组合式 API
- 命名：小驼峰（camelCase）
- 组件分层：**页面容器页** + **纯 UI 子组件**
- 公共组件存放：`components/ui`（shadcn）、`components/common`

### 后端规范
- 变量命名：下划线风格（snake_case）
- 接口参数统一使用 Pydantic 模型接收，禁止零散参数
- 接口严格 Restful 规范：GET 查、POST 新增、PUT 修改、DELETE 删除

### 全局接口返回格式
```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```
- `code=200`：请求成功 / 抓取成功
- `code=500`：浏览器异常 / 抓取失败 / 接口报错
- SSE 数据流：标准 `text/event-stream` 格式

### 通用规范
- 所有魔法数字、URL、刷新频率、超时时间 → 环境变量
- 核心解耦：RPA 抓取、浏览器驱动、XPath 规则、数据解析 完全独立

---

## RPA 抓取核心规则

### XPath 规则
- ❌ **禁止**：浏览器自动生成的绝对路径 XPath
- ✅ **强制**：手写行列文字交叉 XPath
- 文字匹配统一使用 `normalize-space()` 适配隐形空格
- 仅适配 DIV 结构网页表格

### 容错机制
- 抓取失败不闪退，日志记录异常
- 前端/悬浮窗展示空数据状态
- 支持抓取重试（次数、间隔可配）

### 架构原则
RPA 抓取业务、浏览器驱动逻辑、XPath 规则、数据解析逻辑 **完全独立**，与 PyQt6 悬浮窗、前端展示层彻底解耦，支持插拔式拓展。

---

## License

MIT
