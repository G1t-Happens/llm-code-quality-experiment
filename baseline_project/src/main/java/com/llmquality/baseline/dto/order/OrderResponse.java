package com.llmquality.baseline.dto.order;

import com.llmquality.baseline.enums.OrderStatus;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;


/**
 * DTO for order responses.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record OrderResponse(
        Long id,

        String orderNumber,

        Long userId,

        OrderStatus status,

        BigDecimal totalAmount,

        Instant created,

        Instant updated,

        List<OrderItemResponse> items

) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}