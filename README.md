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



### 3. Compatibility

| Sub-characteristic   | Fault Idea                                                           | Code Location                                                  | Description                                                                                                                                                 | ISO Justification                                                                                                         |
|----------------------|----------------------------------------------------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Co-existence**     | Root logger level and appender change                                | `LoggingConfig.java` in `logger()`                             | Appender and log level are set on `ROOT_LOGGER`, affecting all components and modules globally. May degrade performance or mix logs from unrelated modules. | Violates ability to share environment without detrimental impact; other products/components are unintentionally affected. |
| **Co-existence**     | Global JVM timezone set via System.setProperty & TimeZone.setDefault | `LoggingConfig.java` in `logger()`                             | Sets the timezone globally for the entire JVM instead of only for the logger, potentially affecting other modules, libraries, and scheduling operations.    | Violates ability to share environment without detrimental impact; other products/components are unintentionally affected. |
| **Interoperability** | Incorrect MIME type in controller                                    | `UserController.java` in `@PostMapping(consumes="text/plain")` | The API expects JSON (`UserRequest`), but `text/plain` is declared. Clients sending JSON may fail.                                                          | System cannot correctly interpret exchanged information with other systems or clients.                                    |


![Compatibility.png](docs/images/Compatibility.png)



### 4. Usability

| Sub-characteristic                                | Fault Idea                                          | Code Location             | Description                                                                                                                                                                                    | ISO Justification                                                                                                |
|---------------------------------------------------|-----------------------------------------------------|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| **User error protection**                         | Missing `@Valid` / `@Validated` on create endpoint  | `UserController.create()` | The `create()` endpoint does not validate the `UserRequest` DTO. Invalid input (e.g., missing required fields) can lead to a 500 Internal Server Error instead of a clear client-facing error. | Violates ISO 25010 by failing to protect the user from errors; clients cannot easily recover from invalid input. |
| **Appropriateness recognizability**               | LoginRequest DTO field names changed to `x` and `y` | `LoginRequest.java`       | The username and password fields are renamed to `x` and `y`. Clients cannot intuitively know which value corresponds to username or password, making the API confusing to use.                 | Violates ISO 25010 because clients cannot recognize the expected input, reducing API usability and clarity.      |
| **Operability / Appropriateness recognizability** | `PUT` used instead of `PATCH` for partial updates   | `UserController.update()` | The `update()` endpoint uses `PUT`, but partial fields are updated. Clients expecting full replacement may unintentionally behave incorrectly.                                                 | Violates ISO 25010: API is hard to use correctly and does not convey the intended behavior clearly to clients.   |

![Usability -1.png](docs/images/Usability%20-1.png)
![Usability - 2.png](docs/images/Usability%20-%202.png)
![Usability - 3.png](docs/images/Usability%20-%203.png)



### 7. Maintainability

| Sub-characteristic                 | Fault Idea                                    | Code Location                           | Description                                                                                                                                                                             | ISO Justification                                                                                                      |
|------------------------------------|-----------------------------------------------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| **Modularity**                     | Tight coupling between controller and service | `UserController.java`                   | The `UserController` now directly depends on `UserServiceImpl` instead of the `UserService` interface. This creates tight coupling, making testing and swapping implementations harder. | Violates ISO 25010: Lowers maintainability and modularity; changes in the service may force changes in the controller. |
| **Reusability**, **Modifiability** | Removed reusable static constant              | Multiple locations in `UserServiceImpl` | The previously shared USER constant was removed, and the value is repeated manually in multiple locations, reducing the ability to change/reuse consistent values.                      | Violates ISO 25010: Reduces maintainability and increases potential for errors due to duplicated constants.            |
| **Analysability**                  | Rewrite method name to something unclear      | `UserServiceImpl.java`                  | `checkLogin`-Method is rewritten in a way that is unclear, making it difficult to assess the impact of changes or understand the intended behavior.                                     | Violates ISO 25010: Lowers analyzability; developers cannot easily understand or predict the impact of changes.        |

![Maintainability - 1.png](docs/images/Maintainability%20-%201.png)
![Maintainability - 2.png](docs/images/Maintainability%20-%202.png)
![Maintainability - 3.png](docs/images/Maintainability%20-%203.png)