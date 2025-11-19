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
        @NotBlank(groups = Create.class)
        String username,

        @NotBlank(groups = Create.class)
        @Pattern(regexp = "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$",
                message = "Password must be at least 8 characters, contain at least one digit, one lowercase and one uppercase letter.",
                groups = {Create.class, Update.class})
        @Size(min = 8, max = 255, groups = {Create.class, Update.class})
        String password,

        @NotBlank(groups = Create.class)
        @Email(groups = {Create.class, Update.class})
        String email,

        @NotNull(groups = Create.class)
        Boolean admin
) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}
