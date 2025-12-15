# Copilot Instructions for Maven Dependency Web Visualizer

## 1. 角色与目标
你是一位全栈 Python 工程师（精通 FastAPI 和数据可视化）。
**目标**：构建一个 Web 应用程序，允许用户上传 Maven `pom.xml` 文件，解析依赖关系，并通过交互式 Web 界面展示依赖网络、列表以及动态聚合的依赖树。

## 2. 技术栈 (Web Focus)
- **包管理**：**必须使用 `uv`**。
- **后端框架**：**FastAPI** (用于构建 REST API 和服务 HTML)。
- **模板引擎**：**Jinja2** (用于服务端渲染 HTML)。
- **核心逻辑**：
  - **`lxml`**: 解析 XML。
  - **`NetworkX`**: 构建图结构、合并节点、计算依赖路径。
  - **`SQLModel`**: 数据库 ORM (SQLite)。
- **前端技术**：
  - **HTMX**: 用于处理无刷新的文件上传、表格搜索和视图切换。
  - **Cytoscape.js**: **强制使用**此库在前端渲染交互式依赖图（支持节点合并、布局切换）。
  - **Tailwind CSS** (通过 CDN): 用于快速构建现代 UI。

## 3. 数据模型规范
- **Artifact (GAV)**:
  - `group_id`: Optional[str] (默认为 "Unknown").
  - `artifact_id`: str (必须存在).
  - `version`: Optional[str] (默认为 "Unknown").
  - **唯一性逻辑**: 虽然 V 是可选的，但 DB 存储时仍应尽量保留原始信息。在展示层才进行合并。
- **Dependency (Edge)**:
  - 必须记录 `scope` (compile, test, etc.)。

## 4. 核心业务逻辑指令
- **解析容错**：如果在 `pom.xml` 的 properties 或 parent 中找不到 version，**不要报错**，直接赋值为 "Unknown"。
- **节点聚合 (Node Aggregation)**：
  - 提供一个后端服务或逻辑，能够根据用户开关（Show Group? Show Version?），动态重组 NetworkX 图。
  - **合并规则**：如果用户隐藏 Version，则所有 `log4j:1.2` 和 `log4j:2.0` 的节点应合并为同一个 `log4j` 节点，且它们的入边和出边也要合并。
- **依赖方向**：
  - 默认视图：A depends on B (A -> B).
  - Reverse 视图：Who depends on B (A -> B, highlight B's predecessors).

## 5. 开发工作流
- 启动命令：`uv run fastapi dev src/main.py`
- 依赖添加：`uv add fastapi uvicorn python-multipart jinja2 sqlmodel networkx lxml`

## 6. [UI/UX Design System] - VS Code "Quiet Light" Theme

**核心原则**：所有生成的 HTML/CSS 必须模仿 VS Code 的 "Quiet Light" 主题风格。

### 6.1. 配色方案 (Color Palette)
使用 Tailwind CSS 类来实现以下视觉效果：
- **背景 (Backgrounds)**:
  - App Background: `#F3F3F3` (接近 VS Code 的 side bar 颜色).
  - Content/Panel Background: `#FFFFFF` (纯白卡片).
  - Hover Background: `#E8E8E8` (列表项悬停).
- **文字 (Typography Colors)**:
  - Primary Text: `#333333` (深灰，不要纯黑).
  - Secondary/Meta Text: `#767676` (用于 Label 或不重要的信息).
- **边框 (Borders)**: `#E5E5E5` (非常淡的分割线).
- **强调色 (Accents)**:
  - Primary Action (Button/Link): `#0090F1` (VS Code Blue).
  - Success/Valid: `#098658` (VS Code Green).
  - Keyword/Tag: `#800080` (VS Code Purple).

### 6.2. 字体策略 (Typography)
- **通用字体 (Body)**: 使用系统级无衬线字体栈，优先保证清晰度。
  - `font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;`
  - 如果可能，通过 CDN 引入 **Inter** 字体 (Google Fonts)。
- **代码/GAV字体 (Monospace)**:
  - 显示 GroupId, ArtifactId, Version 等数据时，**必须**使用等宽字体。
  - `font-family: "Fira Code", "Consolas", "Monaco", monospace;`
  - 稍微减小字号 (e.g., `text-sm`) 以便在表格中显示更多内容。

### 6.3. 组件风格 (Component Styles)
- **卡片 (Cards)**: 白色背景，无阴影或极浅的阴影 (`shadow-sm`)，1px 的实线边框 (`border-gray-200`)。
- **按钮 (Buttons)**: 扁平化，直角或极小的圆角 (`rounded-sm`)，模仿 VS Code 的原生控件。
- **表格 (Tables)**: 紧凑型 (`table-compact`)，行高较小，便于阅读大量数据。