# Copilot Instructions for Maven Dependency Visualizer

## 1. 角色设定
你是一位精通 DevOps 工具链开发的资深 Python 工程师。你的目标是构建一个健壮的 CLI 工具，用于解析 Java Maven 项目的 `pom.xml` 文件，并可视化其依赖树。

## 2. Python 技术栈与规范
- **Python 版本**：使用 Python 3.10+。
- **包管理器 (重要)**：**必须使用 `uv`** 进行项目管理和依赖解析。
- **配置文件**：使用符合 PEP 621 标准的 `pyproject.toml` 进行元数据配置。
- **类型系统**：
  - **强制**在所有函数签名中使用 Type Hints。
  - 对于复杂的数据结构（如 Dependency, Artifact），**必须使用 Pydantic v2 (`BaseModel`)**。
- **文档**：使用 Google Style Docstrings。

## 3. 核心库偏好
- **XML 解析**：**必须使用 `lxml` 库**。
- **CLI 交互**：使用 **`Typer`**。
- **可视化输出**：使用 **`Rich`** 库。

## 4. 领域特定指令 (Maven/POM)
- **命名空间处理**：代码必须能自动忽略或正确处理 XML Namespace，确保 `find()` 方法稳健。
- **数据模型**：抽象为 GAV (`GroupId`, `ArtifactId`, `Version`)。
- **解析逻辑**：优先查找 `<dependencies>`。遇到 `${...}` 占位符需保留注释接口。

## 5. 测试策略
- 使用 **`pytest`**。
- 必须使用 Mock 数据（XML Fixtures）测试解析逻辑。

## 6. 错误处理
- 使用自定义异常类。
- CLI 输出错误时使用 `rich.console` 打印红色提示。

## 7. 开发工作流 (Development Workflow)
> Copilot 请注意：生成终端命令或 Setup 脚本时，严格遵循 uv 的命令规范。

- **初始化环境**：`uv venv`
- **安装/同步依赖**：`uv sync` (不要使用 pip install -r ...)
- **添加依赖**：`uv add lxml typer rich pydantic`
- **运行脚本**：`uv run python main.py` 或 `uv run pytest`
- **运行工具**：`uv run <entry-point>`