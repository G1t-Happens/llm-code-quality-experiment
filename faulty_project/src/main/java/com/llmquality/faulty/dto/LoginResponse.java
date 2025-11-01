package com.llmquality.faulty.dto;

import jakarta.validation.constraints.NotNull;


/**
 * Response DTO for login operations.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record LoginResponse(

        @NotNull(message = "The success flag is always provided by the API and indicates whether the login was successful.")
        Boolean success

) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}