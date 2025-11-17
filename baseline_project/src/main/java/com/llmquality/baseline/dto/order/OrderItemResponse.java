package com.llmquality.baseline.dto.order;

import java.math.BigDecimal;

public record OrderItemResponse(
        Long productId,
        String productTitle,
        int quantity,
        BigDecimal unitPrice,
        BigDecimal subtotal
) {
}