package com.llmquality.baseline.dto;


import java.time.Instant;

/**
 * Response DTO for login operations.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record LoginResponse(

        String token,

        Instant expiresAt,

        long expiresInSeconds
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}
