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

### 4. Usability

| Sub-characteristic                                | Fault Idea                                          | Code Location             | Description                                                                                                                                                                                    | ISO Justification                                                                                                |
|---------------------------------------------------|-----------------------------------------------------|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| **User error protection**                         | Missing `@Valid` / `@Validated` on create endpoint  | `UserController.create()` | The `create()` endpoint does not validate the `UserRequest` DTO. Invalid input (e.g., missing required fields) can lead to a 500 Internal Server Error instead of a clear client-facing error. | Violates ISO 25010 by failing to protect the user from errors; clients cannot easily recover from invalid input. |
| **Appropriateness recognizability**               | LoginRequest DTO field names changed to `x` and `y` | `LoginRequest.java`       | The username and password fields are renamed to `x` and `y`. Clients cannot intuitively know which value corresponds to username or password, making the API confusing to use.                 | Violates ISO 25010 because clients cannot recognize the expected input, reducing API usability and clarity.      |
| **Operability / Appropriateness recognizability** | `PUT` used instead of `PATCH` for partial updates   | `UserController.update()` | The `update()` endpoint uses `PUT`, but only partial fields are updated. Clients expecting full replacement may unintentionally overwrite data or behave incorrectly.                          | Violates ISO 25010: API is hard to use correctly and does not convey the intended behavior clearly to clients.   |

![Usability -1.png](docs/images/Usability%20-1.png)
![Usability - 2.png](docs/images/Usability%20-%202.png)
![Usability - 3.png](docs/images/Usability%20-%203.png)