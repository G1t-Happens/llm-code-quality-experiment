package com.llmquality.baseline.dto;

import jakarta.validation.constraints.*;


/**
 * Response DTO for User information.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getters, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record UserResponse(

        @NotNull(message = "The ID is always provided by the API and cannot be null.")
        @Positive(message = "The ID will always be a positive number.")
        Long id,

        @NotBlank(message = "The username will always be provided and cannot be empty.")
        @Size(max = 255, message = "The username will be a maximum of 255 characters.")
        String name,

        @NotBlank(message = "The email will always be provided and cannot be empty.")
        @Email(message = "The email will be in a valid format.")
        @Size(max = 255, message = "The email will be a maximum of 255 characters.")
        String email,

        @NotNull(message = "The admin flag will always be provided and cannot be null. It indicates whether the user has admin rights.")
        Boolean admin

) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}
