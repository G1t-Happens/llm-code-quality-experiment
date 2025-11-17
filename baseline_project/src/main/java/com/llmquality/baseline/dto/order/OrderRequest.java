package com.llmquality.baseline.dto.order;

import com.llmquality.baseline.dto.order.validation.OrderValidationGroups;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;


/**
 * DTO for order requests.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record OrderRequest(

        @NotEmpty(message = "An order must contain at least one item", groups = OrderValidationGroups.Create.class)
        @Size(max = 50, message = "An order cannot have more than 50 items", groups = OrderValidationGroups.Create.class)
        List<@Valid OrderItemRequest> items
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}