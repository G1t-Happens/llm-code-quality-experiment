package com.llmquality.baseline.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;


/**
 * Data Transfer Object (DTO) for user login requests.
 * <p>
 * Contains the username and password fields with validation constraints
 * to ensure non-blank input and enforce maximum length.
 * </p>
 */
public record LoginRequest(

        @NotBlank(message = "Username must not be blank")
        @Size(max = 255, message = "Username must be at most 255 characters long")
        String username,

        @NotBlank(message = "Password must not be blank")
        @Size(max = 255, message = "Password must be at most 255 characters long")
        String password
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}
