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


### 2. Performance Efficiency

| Sub-characteristic       | Fault Idea                                                    | Code Location                        | Description                                                                                                                                  | ISO Justification                                                            |
|--------------------------|---------------------------------------------------------------|--------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| **Time Behavior**        | Load all users first, and then apply pagination               | `listAll()` in `UserServiceImpl`     | Method loads all users from DB and paginates in memory → slow response for large data sets                                                   | Function is correct but response time is insufficient under load             |
| **Resource Utilization** | PasswordEncoder instantiated per request instead of singleton | `save()`, `update()`, `checkLogin()` | Each method call creates a new `BCryptPasswordEncoder` → high CPU and memory usage                                                           | Unnecessary resource consumption reduces efficiency                          |
| **Capacity**             | No limits on data processing / paging                         | `listAll()` in `UserServiceImpl`     | Loading all users into memory without limit → simulates memory/CPU stress; cannot fully embed as real capacity faults are resource-dependent | Application cannot handle unlimited resources → capacity constraint violated |

![Performance efficiency - 1.png](docs/images/Performance%20efficiency%20-%201.png)
![Performance efficiency - 2.png](docs/images/Performance%20efficiency%20-%202.png)