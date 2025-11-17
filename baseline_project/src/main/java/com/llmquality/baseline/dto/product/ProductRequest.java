package com.llmquality.baseline.dto.product;

import com.llmquality.baseline.dto.product.validation.ProductValidationGroups;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;


/**
 * Request DTO for product information.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getters, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * Contains the title, description, price and stock.
 * </p>
 */
public record ProductRequest(
        @NotBlank(message = "Title must not be blank", groups = ProductValidationGroups.Create.class)
        String title,

        @NotBlank(message = "Description must not be blank", groups = ProductValidationGroups.Create.class)
        @Size(max = 2000, message = "Description too long", groups = {ProductValidationGroups.Create.class, ProductValidationGroups.Update.class})
        String description,

        @Min(value = 0, message = "Price must be >= 0", groups = ProductValidationGroups.Create.class)
        BigDecimal price,

        @Min(value = 0, message = "Stock must be >= 0", groups = ProductValidationGroups.Create.class)
        Integer stock
) {
    // You can add custom methods here if needed, e.g., convenience methods or formatting helpers.
}