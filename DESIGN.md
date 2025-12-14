# Design Doc for J-Dep Analyzer

## 1. 系统架构 (Web App)

本工具（J-Dep Analyzer）旨在解决微服务架构下 Maven 依赖管理混乱的问题。它能扫描整个文件夹下的所有 Java 项目，构建一个全量的**依赖知识图谱**，回答诸如“如果我们升级 Log4j，会影响哪些服务？”之类的问题。

采用标准的 MVC 架构：

- **Model**: SQLModel (SQLite 存储解析后的原子数据).
- **Controller (API)**: FastAPI Endpoints 处理上传、查询和图数据生成.
- **View**: Jinja2 Templates + Cytoscape.js Canvas.

## 2. 数据模型 (Schema)

### 2.1 Artifact (Node)

```python
class Artifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: str = Field(default="Unknown", index=True)
    artifact_id: str = Field(index=True)
    version: str = Field(default="Unknown")
    
    # Computed property for display
    @property
    def gav_str(self):
        return f"{self.group_id}:{self.artifact_id}:{self.version}"
```

#### 2.2 Dependency (Edge)

```python
class Dependency(SQLModel, table=True):
    source_id: int = Field(foreign_key="artifact.id")
    target_id: int = Field(foreign_key="artifact.id")
    scope: str = "compile"
```

## 3. 功能模块设计

### 3.1 文件上传与解析 (`POST /upload`)

- **UI**: 提供一个拖拽上传区域 (Dropzone)，支持一次上传多个 `pom.xml`。
- **Logic**:
  - 接收 `List[UploadFile]`。
  - 使用 `lxml` 解析。
  - 遇到 `${...}` 无法解析时，Version 存为 "Unknown"。
  - "Upsert" 逻辑：如果 GAV 已存在，忽略；否则插入 DB。

### 3.2 视图 A: 全局依赖概览 (`GET /graph/global`)

- **功能**: 展示 DB 中所有 Artifact 的关系网。
- **聚合参数**: `?show_group=bool&show_version=bool`
- **算法 (Graph Aggregation)**:
  - 从 DB 加载全量原子图 (Atomic Graph)。
    - 如果 `show_version=False`:
    - 遍历所有节点，生成新 Key (例如 `groupId:artifactId`)。
    - 将所有旧节点的边 (Edges) 迁移到新 Key 上。
    - 使用 `nx.contracted_nodes` 或重建图来实现合并。
  - 返回 JSON 格式的 Elements 给 Cytoscape.js 渲染。

### 3.3 视图 B: 依赖对列表 (Pair List) (`GET /dependencies/list`)

- **UI**: 双栏布局表格。
- **Group 1 (Source)**: `G | A | V`
- **Group 2 (Target)**: `G | A | V`
- **交互**:
  - 每一行是可点击的 (`<tr hx-get="/details/{id in Group 1}" ...>`)。
  - 顶部提供 Filter 输入框 (Filter by ArtifactId)。
  - 提供 Checkbox: "Ignore Version", "Ignore GroupId"（勾选后，表格内容需去重聚合）。
  - 提供 Export 按钮，导出当前视图为 CSV。

### 3.4 视图 C: 详细依赖透视 (`GET /details/{artifact_id}`)

- **触发**: 用户在视图 B 中点击某一行。
- **UI**:
  - 左侧：节点信息卡片。
  - 右侧：以该节点为中心的局部图谱。
- **功能**:
  - **Forward Tree**: 它依赖了谁？(层级：1层, 2层, 或 All)。
  - **Reverse Tree**: 谁依赖了它？(Impact Analysis)。
- **动态聚合**: 同样支持顶部的 "Hide Version" 开关。如果隐藏 Version，则显示聚合后的“通用组件”关系。

## 4. API 接口设计 (FastAPI)

- `POST /api/upload`: 上传 POMs。
- `GET /api/artifacts`: 获取列表数据 (JSON)。
- `GET /api/graph/data`: 获取图数据 (JSON, Cytoscape format)。
  - **Params**: `root_id` (optional), `direction` (forward/reverse), `aggregate_version` (bool), `aggregate_group` (bool)。
- `GET /`: 主页 (Dashboard)。
- `GET /list`: 列表页 HTML。
- `GET /visualize/{id}`: 详情页 HTML。

## 5. 前端展示逻辑 (Cytoscape.js Style)

### Nodes

- 如果 Version 存在，显示为圆形。
- 如果 Version 被聚合 (Hidden)，显示为矩形或是更大的圆，Label 只有 ArtifactId。
- 颜色编码：Source 节点为蓝色，Target 为灰色，选中的中心节点为红色。

### Layout

- 使用 cose-bilkent 或 dagre (层级布局) 来展示依赖树。
