from __future__ import annotations

from pathlib import Path

from j_dep_analyzer.models import MavenProject
from j_dep_analyzer.parser import parse_pom


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_pom_without_namespace(tmp_path: Path) -> None:
    pom = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>

  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.12</version>
      <scope>compile</scope>
    </dependency>
  </dependencies>
</project>
"""
    path = _write(tmp_path, "pom.xml", pom)
    model = parse_pom(path)

    assert isinstance(model, MavenProject)
    assert model.project.group_id == "com.acme"
    assert model.project.artifact_id == "demo"
    assert model.project.version == "1.0.0"
    assert len(model.dependencies) == 1
    assert model.dependencies[0].gav.group_id == "org.slf4j"
    assert model.dependencies[0].gav.artifact_id == "slf4j-api"
    assert model.dependencies[0].gav.version == "2.0.12"


def test_parse_pom_with_namespace(tmp_path: Path) -> None:
    pom = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project xmlns=\"http://maven.apache.org/POM/4.0.0\">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>

  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
      <optional>false</optional>
    </dependency>
  </dependencies>
</project>
"""
    path = _write(tmp_path, "pom.xml", pom)
    model = parse_pom(path)

    assert model.project.compact() == "com.acme:demo:1.0.0"
    assert len(model.dependencies) == 1
    dep = model.dependencies[0]
    assert dep.gav.compact() == "junit:junit:4.13.2"
    assert dep.scope == "test"
    assert dep.optional is False


def test_preserve_property_placeholders(tmp_path: Path) -> None:
    pom = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>demo</artifactId>

  <dependencies>
    <dependency>
      <groupId>org.example</groupId>
      <artifactId>lib</artifactId>
      <version>${lib.version}</version>
    </dependency>
  </dependencies>
</project>
"""
    path = _write(tmp_path, "pom.xml", pom)
    model = parse_pom(path)

    assert len(model.dependencies) == 1
    assert model.dependencies[0].gav.version == "${lib.version}"
