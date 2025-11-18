package com.llmquality.baseline.dto;

import com.llmquality.baseline.dto.validation.UserValidationGroups;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;


/**
 * Data Transfer Object (DTO) for creating or updating a User.
 * <p>
 * Contains user input fields with validation annotations for create and update operations.
 * </p>
 */
public record UserRequest(
        @NotBlank(groups = {UserValidationGroups.Create.class})
        String username,

        @NotBlank(groups = UserValidationGroups.Create.class)
        @Pattern(regexp = "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$",
                message = "Password must be at least 8 characters long, contain at least one number, one lowercase and one uppercase letter.",
                groups = {UserValidationGroups.Update.class, UserValidationGroups.Create.class}
        )
        String password,

        @NotBlank(groups = UserValidationGroups.Create.class)
        @Email(groups = {UserValidationGroups.Update.class, UserValidationGroups.Create.class})
        String email,

        @NotNull(groups = UserValidationGroups.Create.class)
        Boolean admin
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}
