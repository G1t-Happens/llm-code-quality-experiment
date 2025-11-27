package com.llmquality.baseline.dto;

import jakarta.validation.constraints.*;

import static com.llmquality.baseline.dto.validation.UserValidationGroups.*;


/**
 * Data Transfer Object (DTO) for creating or updating a User.
 * <p>
 * Contains user input fields with validation annotations for create and update operations.
 * </p>
 */
public record UserRequest(

        @NotBlank(groups = Create.class, message = "Username is required")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "Username must not be empty or consist only of whitespace")
        String username,

        @NotBlank(groups = Create.class, message = "Password is required on create")
        @Pattern(regexp = "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$",
                groups = {Create.class, Update.class},
                message = "Password must be at least 8 characters, contain number, lowercase and uppercase")
        @Size(min = 8, max = 255, groups = {Create.class, Update.class})
        String password,

        @NotBlank(groups = Create.class, message = "Email is required on create")
        @Email(groups = {Create.class, Update.class}, message = "Invalid email format")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "Email must not be empty or consist only of whitespace")
        String email,

        @NotNull(groups = Create.class, message = "Admin flag is required on create")
        Boolean admin
) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}
