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




### 2. Performance Efficiency

| Sub-characteristic       | Fault Idea                                                    | Code Location                    | Description                                                                                | ISO Justification                                                |
|--------------------------|---------------------------------------------------------------|----------------------------------|--------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| **Time Behavior**        | Load all users first, and then apply pagination               | `listAll()` in `UserServiceImpl` | Method loads all users from DB and paginates in memory → slow response for large data sets | Function is correct but response time is insufficient under load |
| **Resource Utilization** | PasswordEncoder instantiated per request instead of singleton | `save()` in `UserServiceImpl`    | Each method call creates a new `BCryptPasswordEncoder` → high CPU and memory usage         | Unnecessary resource consumption reduces efficiency              |
| **Resource Utilization** | PasswordEncoder instantiated per request instead of singleton | `update()` in `UserServiceImpl`  | Each method call creates a new `BCryptPasswordEncoder` → high CPU and memory usage         | Unnecessary resource consumption reduces efficiency              |
![Performance efficiency - 1.png](docs/images/Performance%20efficiency%20-%201.png)
![Performance efficiency - 2.png](docs/images/Performance%20efficiency%20-%202.png)