package com.llmquality.baseline.dto.order;

import java.math.BigDecimal;


/**
 * DTO for order item responses.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record OrderItemResponse(

        Long productId,

        String productTitle,

        int quantity,

        BigDecimal unitPrice,

        BigDecimal subtotal
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}