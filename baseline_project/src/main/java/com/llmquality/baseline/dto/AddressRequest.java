package com.llmquality.baseline.dto;

import com.llmquality.baseline.dto.validation.AddressValidationGroups;
import com.llmquality.baseline.enums.AddressType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;


/**
 * Request DTO for addresses.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record AddressRequest(
        @NotBlank(groups = AddressValidationGroups.Create.class)
        @Size(max = 255, message = "Street must be at most 255 characters long")
        String street,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        @Size(max = 255, message = "HouseNumber must be at most 255 characters long")
        String houseNumber,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        @Size(max = 255, message = "PostalCode must be at most 255 characters long")
        String postalCode,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        @Size(max = 255, message = "City must be at most 255 characters long")
        String city,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        @Size(max = 255, message = "Country must be at most 255 characters long")
        String country,

        @NotNull(groups = AddressValidationGroups.Create.class)
        AddressType addressType
) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}