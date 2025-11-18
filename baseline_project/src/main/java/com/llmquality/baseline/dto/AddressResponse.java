package com.llmquality.baseline.dto;

import com.llmquality.baseline.enums.AddressType;


/**
 * Response DTO for addresses.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record AddressResponse(

        Long id,

        String street,

        String houseNumber,

        String postalCode,

        String city,

        String country,

        AddressType addressType,
        Long userId
) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}
