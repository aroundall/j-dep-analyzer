# Design Doc for J-Dep Analyzer

## 1. 系统概述 (Overview)

本工具（J-Dep Analyzer）旨在解决微服务架构下 Maven 依赖管理混乱的问题。它能扫描整个文件夹下的所有 Java 项目，构建一个全量的**依赖知识图谱**，回答诸如“如果我们升级 Log4j，会影响哪些服务？”之类的问题。

## 2. 架构设计 (Architecture)

### 2.1 核心流程

1. **Ingest (摄取)**: 递归扫描目录 -> 解析 `pom.xml` or "\<artifact\>.pom" -> 提取 GAV 和 Dependency。
2. **Resolve (解析/对齐)**: 
   - 处理 Parent POM 继承（填充子模块缺失的 Version/GroupId）。
   - 处理 `${project.version}` 等属性占位符。
3. **Persist (存储)**: 将清洗后的数据存入 SQLite (`dependencies.db`)。
4. **Analyze (分析)**: 从 SQLite 加载数据 -> 构建 `NetworkX.DiGraph` -> 执行图算法。
5. **Visualize (展示)**: CLI 列表 (Rich) 或 HTML 交互图 (Pyvis)。

### 2.2 数据流图 (Mermaid)

```mermaid
flowchart TD
    A[User Input: Folder Path] --> B(Scanner)
    B --> C{pom Files}
    C -->|lxml| D[Parser]
    D --> E[Raw Artifacts]
    E --> F[Graph Builder]
    F -->|Resolve Versions| G[SQLModel/SQLite]
    
    G --> H[Analyzer Engine]
    H -->|NetworkX| I[Query: Reverse Dependency]
    H -->|NetworkX| J[Query: Dependency Path]
    
    I --> K[Rich Console Output]
    J --> L[Pyvis HTML Report]