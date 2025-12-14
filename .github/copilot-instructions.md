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