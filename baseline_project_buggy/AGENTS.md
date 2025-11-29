# AGENTS.md
1. Toolchain: Java 21, Spring Boot 3.5.7, use `./gradlew`.
2. Full build: `./gradlew clean build` runs compile+tests.
3. Boot the API locally with `./gradlew bootRun` (Flyway + dotenv).
4. Run the suite via `./gradlew test`; coverage at `build/reports/jacoco/test/html`.
5. Single test syntax: `./gradlew test --tests com.llmquality.baseline.BaselineProjectApplicationTests`.
6. Lint/check pipeline is `./gradlew check jacocoTestReport`; no extra linters configured.
7. No Cursor (.cursor/rules) or Copilot (.github/copilot-instructions.md) rule files exist.
8. Organize imports: project, third-party, Jakarta/Spring, then static; blank line between groups and before classes.
9. Prefer constructor injection with `final` fields; avoid field/setter injection.
10. DTOs are Java `record`s with Jakarta validation groups on their own lines.
11. Services/controllers annotate with `@Transactional`/`@Validated`; mark method params `final`.
12. MapStruct handles entity ↔ DTO mapping; don’t duplicate manual mapping.
13. Pagination uses `Pageable` + `PagedResponse.fromPage`; reuse this helper.
14. Security rules live in `SecurityExpressions`; reuse its helpers inside `@PreAuthorize`.
15. Logging: declare `private static final Logger LOG` and log entry/exit with placeholders.
16. Exceptions: throw `ResourceNotFoundException`, `ResourceAlreadyExistsException`, `UnauthorizedException` with context.
17. Validation errors bubble through `GlobalExceptionHandler`; never swallow framework exceptions.
18. Use UpperCamelCase for classes, lowerCamelCase for members, UPPER_SNAKE_CASE for constants.
19. Keep controllers thin—delegate to services, return DTOs, and prefer repository/parameterized queries over concatenated SQL.
20. Follow record/DTO validation patterns already present before adding new transport types.