package com.llmquality.baseline.dto.order;

import com.llmquality.baseline.dto.order.validation.OrderValidationGroups;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;


/**
 * DTO for order item responses.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record OrderItemRequest(

        @NotNull(message = "productId must not be null", groups = OrderValidationGroups.Create.class)
        @Positive(message = "productId must be a positive number", groups = OrderValidationGroups.Create.class)
        Long productId,

        @NotNull(message = "quantity must not be null", groups = OrderValidationGroups.Create.class)
        @Min(value = 1, message = "quantity must be at least 1", groups = OrderValidationGroups.Create.class)
        @Max(value = 1000, message = "quantity cannot exceed 1000", groups = OrderValidationGroups.Create.class)
        Integer quantity
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}