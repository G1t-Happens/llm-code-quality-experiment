package com.llmquality.baseline.dto;


/**
 * Response DTO for User information.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getters, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record UserResponse(

        Long id,

        String name,

        String email,

        Boolean admin

) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}
