package com.llmquality.baseline.dto.order;

import com.llmquality.baseline.enums.OrderStatus;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;


public record OrderResponse(
        Long id,
        String orderNumber,
        Long userId,
        OrderStatus status,
        BigDecimal totalAmount,
        Instant createdAt,
        Instant updatedAt,
        List<OrderItemResponse> items
) {
}