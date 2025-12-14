# Copilot Instructions for Maven Graph Analyzer

## 1. 角色与目标
你是一位精通 Python 和 Build Engineering 的资深专家。
**目标**：构建一个 CLI 工具，解析多个 Maven `pom.xml` 文件，将其转化为**有向图 (Directed Graph)**，并提供依赖查询（特别是反向依赖）和可视化功能。

## 2. 技术栈 (严格执行)
- **包管理**：**必须使用 `uv`** (Astral) 进行依赖管理和脚本运行。
- **核心语言**：Python 3.10+ (大量使用 Type Hints)。
- **数据结构/图算法**：**`NetworkX`** (用于构建依赖图谱)。
- **持久化/ORM**：**`SQLModel`** (结合 SQLAlchemy + Pydantic)。
- **CLI 框架**：**`Typer`**。
- **XML 解析**：**`lxml`** (必须处理 Namespaces)。
- **可视化**：
  - 终端：**`Rich`** (Tree view, Tables)。
  - Web/HTML：**`Pyvis`** (Interactive Network Graph)。

## 3. 代码规范
- **类型系统**：所有函数必须有类型注解。复杂对象必须是 `SQLModel` 或 `Pydantic` 模型。
- **路径处理**：使用 `pathlib.Path` 而不是 `os.path`。
- **错误处理**：使用 `rich.console` 打印红色错误信息，严禁直接打印 Traceback 给最终用户。

## 4. 领域模型规则 (Maven & Graph)
- **唯一标识 (ID)**：Artifact ID 格式统一为 `groupId:artifactId:version` (GAV)。
- **图的方向**：
  - **Node**: Artifact (Project 或 Library)。
  - **Edge**: Dependency。
  - **方向性**: 如果 A 依赖 B，边从 A 指向 B (`A -> B`)。
  - **反向查询**: 查询“谁依赖了 B”，即寻找 B 的入度节点 (Predecessors)。
- **XML 解析细节**：
  - 必须容忍 XML Namespace。
  - 必须能够提取 `<parent>` 标签中的版本号来补全子模块的缺失版本。
  - 如果 `<version>` 标签缺失，但又根据parent或者properties无法推断出来，则标记version为“Unknown”。

## 5. 开发工作流指令
> 当生成 setup 命令或运行指令时，请使用以下格式：
- 初始化/添加依赖：`uv init`, `uv add networkx sqlmodel typer rich lxml pyvis`
- 运行测试：`uv run pytest`
- 运行应用：`uv run python -m src.main`