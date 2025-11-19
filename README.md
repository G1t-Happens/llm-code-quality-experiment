# LLM Code Quality Experiment

## Overview

This repository contains a controlled experiment evaluating the capability of large language models (LLMs) to detect and
analyze software quality issues in applications.

**On the branch _main-enhanced-faulty_ you can find the project with intentionally seeded errors to evaluate the detection capabilities of different analysis approaches**

## Repository Structure

```text
llm-code-quality-experiment/
├── baseline_project/    # Clean, ISO25010-compliant reference project
├── docs/                # Code extraction script & Code diff images
└── README.md
```

- **baseline_project**: Reference implementation with high-quality - clean code.
## Goals

- Assess LLMs' effectiveness in static and dynamic code analysis
- Compare LLM-assisted analysis with classical tools (e.g., SonarQube)
- Evaluate the impact of prompt design and model choice on error detection

## Technology Stack

- Java 21
- Spring Boot
- REST API
- JUnit 5 for testing