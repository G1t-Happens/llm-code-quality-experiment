# AGENTS.md

## Build/Lint/Test Commands
- Build: `./gradlew build`
- Run app: `./gradlew bootRun`
- Test all: `./gradlew test`
- Test single class: `./gradlew test --tests com.llmquality.baseline.controller.UserControllerTest`
- Check (test+compile): `./gradlew check`
- Clean: `./gradlew clean`

## Code Style Guidelines
- Java 21, Spring Boot 3.5.7
- Package: com.llmquality.baseline.*
- Imports: project DTOs/services first, then Jakarta/Spring imports, static last
- Naming: camelCase methods/vars, PascalCase classes, snake_case none
- DI: constructor injection (@Autowired optional)
- Security: @PreAuthorize with @sec expressions (SecurityExpressions.java)
- Validation: @Valid + groups (UserValidationGroups)
- Mapping: MapStruct (AddressMapper, UserMapper)
- Exceptions: custom (ResourceNotFoundException etc.), GlobalExceptionHandler
- No Lombok; manual getters/setters/ctors
- No inline comments; clean code
- Enums: AddressType, Role
- JPA entities: User, Address w/ relationships
- Flyway migrations in src/main/resources/db/migration