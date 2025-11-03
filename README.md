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

### 3. Compatibility

| Sub-characteristic   | Fault Idea                                                           | Code Location                                                  | Description                                                                                                                                                 | ISO Justification                                                                                                         |
|----------------------|----------------------------------------------------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Co-existence**     | Root logger level and appender change                                | `LoggingConfig.java` in `logger()`                             | Appender and log level are set on `ROOT_LOGGER`, affecting all components and modules globally. May degrade performance or mix logs from unrelated modules. | Violates ability to share environment without detrimental impact; other products/components are unintentionally affected. |
| **Co-existence**     | Global JVM timezone set via System.setProperty & TimeZone.setDefault | `LoggingConfig.java` in `logger()`                             | Sets the timezone globally for the entire JVM instead of only for the logger, potentially affecting other modules, libraries, and scheduling operations.    | Violates ability to share environment without detrimental impact; other products/components are unintentionally affected. |
| **Interoperability** | Incorrect MIME type in controller                                    | `UserController.java` in `@PostMapping(consumes="text/plain")` | The API expects JSON (`UserRequest`), but `text/plain` is declared. Clients sending JSON may fail.                                                          | System cannot correctly interpret exchanged information with other systems or clients.                                    |


![Compatibility.png](docs/images/Compatibility.png)