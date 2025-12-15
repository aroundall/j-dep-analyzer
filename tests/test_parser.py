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
    assert model.dependencies[0].gav.version == "Unknown"


def test_unresolved_placeholders_in_real_pom_become_unknown() -> None:
    pom_path = Path(__file__).parent / "data" / "sample-pom" / "jackson-databind-2.19.4.pom"
    model = parse_pom(pom_path)

    # This POM declares jackson-core and jackson-annotations versions as placeholders
    # (${jackson.version.*}) without defining them in <properties>.
    versions = {d.gav.artifact_id: d.gav.version for d in model.dependencies}
    assert versions.get("jackson-core") == "Unknown"
    assert versions.get("jackson-annotations") == "Unknown"


def test_inherit_version_from_parent(tmp_path: Path) -> None:
    pom = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project xmlns=\"http://maven.apache.org/POM/4.0.0\">
  <modelVersion>4.0.0</modelVersion>

  <parent>
    <groupId>com.acme</groupId>
    <artifactId>parent</artifactId>
    <version>9.9.9</version>
  </parent>

  <artifactId>child</artifactId>
</project>
"""
    path = _write(tmp_path, "pom.xml", pom)
    model = parse_pom(path)
    assert model.project.compact() == "com.acme:child:9.9.9"


def test_parse_parent_as_dependency(tmp_path: Path) -> None:
    pom = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project xmlns=\"http://maven.apache.org/POM/4.0.0\">
  <modelVersion>4.0.0</modelVersion>

  <parent>
    <groupId>com.acme</groupId>
    <artifactId>parent</artifactId>
    <version>9.9.9</version>
  </parent>

  <groupId>com.acme.child</groupId>
  <artifactId>child</artifactId>
  <version>1.0.0</version>

  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.12</version>
    </dependency>
  </dependencies>
</project>
"""
    path = _write(tmp_path, "pom.xml", pom)
    model = parse_pom(path)

    dep_keys = {(d.gav.compact(), d.scope) for d in model.dependencies}
    assert ("com.acme:parent:9.9.9", "parent") in dep_keys
    assert ("org.slf4j:slf4j-api:2.0.12", None) in dep_keys


def test_resolve_properties_for_dependency_version(tmp_path: Path) -> None:
    pom = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>demo</artifactId>
  <version>1.0.0</version>

  <properties>
    <lib.version>2.3.4</lib.version>
  </properties>

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
    assert model.dependencies[0].gav.compact() == "org.example:lib:2.3.4"
