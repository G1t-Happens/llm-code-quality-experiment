package com.llmquality.baseline.dto.product;

import java.math.BigDecimal;
import java.time.Instant;


/**
 * Response DTO for product information.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getters, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * Contains the id, title, description, price and stock & metadata.
 * </p>
 */
public record ProductResponse(

        Long id,

        String title,

        String description,

        BigDecimal price,

        Integer stock,

        Instant created,

        Instant updated
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}
