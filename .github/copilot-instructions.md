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
  - **`SQLModel`**: 数据库 ORM。
    - **Local**: SQLite (`sqlite:///dependencies.db`).
    - **GCP**: Cloud SQL PostgreSQL via `cloud-sql-python-connector` + `pg8000` (IAM Auth).
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

## 6. [UI/UX Design System] - Modern Material (Indigo/Slate)

**核心原则**：现代、简洁、Material UI 风格 (Inspired)，使用 Tailwind CSS 构建。强调高对比度、阴影带来的层级感以及圆角设计。

### 6.1. 配色方案 (Color Palette)
使用 `tailwind.config` 中定义的扩展颜色：
- **Primary Brand**: Indigo (`#6366f1` / `primary-500` to `#4f46e5` / `primary-600`).
- **背景 (Backgrounds)**:
  - App Background: `#f8fafc` (Slate 50).
  - Surface/Card: `#ffffff` (White).
  - Hover/Highlight: `gray-50` or `indigo-50`.
- **文字 (Typography Colors)**:
  - Primary Text: `#1e293b` (Slate 800).
  - Secondary Text: `#64748b` (Slate 500).
- **功能色 (Functional)**:
  - Success: Green (e.g., compile scope).
  - Test: Purple (e.g., test scope).
  - Error: Red.

### 6.2. 字体策略 (Typography)
- **UI 字体 (Sans)**: `Inter`, `Roboto`, `sans-serif`. 优先使用 **Inter**。
- **代码字体 (Mono)**: `Fira Code`, `monospace`. 用于展示 GroupId, ArtifactId, Version 等。

### 6.3. 组件风格 (Component Styles)
- **阴影 (Shadows)**: 使用自定义的 `shadow-mate-1`, `shadow-mate-2` 等，营造悬浮感。
- **圆角 (Radius)**: 
  - 卡片/容器: `rounded-xl` (较大圆角).
  - 按钮/Badge: `rounded-full` or `rounded-lg`.
- **图标 (Icons)**: Google **Material Symbols Outlined** (Sharp & Clean).
- **交互 (Interactions)**: 按钮支持 Ripple 效果 (可选)，卡片和行项支持 Hover 提升效果 (`hover:shadow-mate-2`).
- **布局 (Layout)**: 顶部导航栏 (Sticky Header) + 居中响应式主体内容 (`max-w-7xl mx-auto`).

## 7. Cloud Infrastructure & Database (GCP)
- **数据库连接原则**：
  - **禁止** 在生产环境使用直接的 TCP/IP 连接字符串 (e.g., `postgresql://user:pass@IP:5432/...`)。
  - **必须** 使用 `cloud-sql-python-connector` 创建连接池。
  - **驱动**：指定使用 `pg8000` (纯 Python, 兼容性好)。
  - **认证**：优先开启 `enable_iam_auth=True`，避免在代码或配置中硬编码数据库密码。
- **环境配置 (Environment Variables)**：
  - `JDEP_DB_TYPE`: `sqlite` (默认) 或 `postgresql`.
  - `JDEP_DB_HOST`: CloudSQL Instance Connection Name (e.g., `project:region:instance`).
  - `JDEP_DB_USER`: IAM Service Account User (e.g., `sa-name@project.iam`).
  - `JDEP_GCP_CREDENTIALS`: (Optional) 本地开发时指向 Service Account JSON Key 的路径。
  - **注意**：应用启动时需根据 `JDEP_DB_TYPE` 自动切换 `create_engine` 逻辑。