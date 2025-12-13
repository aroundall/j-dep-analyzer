# Design Doc for J-Dep Analyzer

## Overview

The J-Dep Analyzer is a tool designed to analyze Java project dependencies. It analyzes Maven pom.xml files. The primary goal of this tool is to help developers understand the structure of their codebase, identify potential issues related to dependencies, and optimize the overall architecture of their projects.

## Features

- **Dependency Analysis**: Parse Maven `pom.xml` files to extract and analyze project dependencies.
- **Visualization**: Provide a visual representation of the dependency tree using the Rich library.
- **CLI Interface**: A command-line interface built with Typer for easy interaction.
- **Error Handling**: Robust error handling with custom exceptions and user-friendly messages.
- **Testing**: Comprehensive test suite using pytest with mock data for various scenarios.
