# LLM Code Quality Experiment

## Overview

This repository contains a controlled experiment evaluating the capability of large language models (LLMs) to detect and
analyze software quality issues in Java Spring Boot applications.

## Repository Structure

```text
llm-code-quality-experiment/
├── baseline_project/    # Clean, ISO25010-compliant reference project
├── faulty_project/      # Same project with injected errors for testing
└── README.md
```

- **baseline_project**: Reference implementation with high-quality - clean code.
- **faulty_project**: Contains intentional errors to evaluate detection capabilities of different analysis approaches.

## Goals

- Assess LLMs' effectiveness in static and dynamic code analysis
- Compare LLM-assisted analysis with classical tools (e.g., SonarQube)
- Evaluate the impact of prompt design and model choice on error detection

## Technology Stack

- Java 21
- Spring Boot
- REST API
- JUnit 5 for testing

## Built-in error categorized according to the ISO 25010 quality model

### 1. Functional Suitability

| Sub-characteristic             | Fault Idea                     | Code Location                        | Description                                                                                    | ISO Justification                                                              |
|--------------------------------|--------------------------------|--------------------------------------|------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **Functional Completeness**    | Repository delete call removed | `delete()` in `UserServiceImpl`      | Delete operation does not actually remove the entity → functionality incomplete                | Part of the required functionality is missing                                  |
| **Functional Correctness**     | Plaintext password comparison  | `checkLogin()`  in `UserServiceImpl` | Login produces incorrect result due to comparing plaintext password instead of hashed password | Function produces incorrect outcomes                                           |
| **Functional Appropriateness** | Double hashing of password     | `update()`   in `UserServiceImpl`    | Password is hashed twice, making update unnecessarily restrictive and potentially unusable     | Function not implemented in a way that effectively supports the intended tasks |
![Functional Suitability.png](docs/images/Functional%20Suitability.png)

