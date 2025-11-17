package com.llmquality.baseline.dto.order;

import jakarta.validation.constraints.Min;


public record OrderItemRequest(
        Long productId,
        @Min(1) int quantity
) {
}