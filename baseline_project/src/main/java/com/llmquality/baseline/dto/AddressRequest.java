package com.llmquality.baseline.dto;

import com.llmquality.baseline.enums.AddressType;
import jakarta.validation.constraints.*;

import static com.llmquality.baseline.dto.validation.AddressValidationGroups.*;


/**
 * Request DTO for addresses.
 * <p>
 * This is a Java {@code record}, which is immutable and automatically provides
 * a constructor, getter, {@code equals()}, {@code hashCode()}, and {@code toString()} methods.
 * Introduced in Java 17.
 * </p>
 */
public record AddressRequest(

        @NotBlank(groups = Create.class, message = "SomeValue is required on create")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "SomeValue must not be empty or consist only of whitespace")
        @Size(max = 255, message = "SomeValue must be at most 255 characters long")
        String someValue,

        @NotBlank(groups = Create.class, message = "House number is required on create")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "House number must not be empty or consist only of whitespace")
        @Size(max = 255)
        String houseNumber,

        @NotBlank(groups = Create.class, message = "Postal code is required on create")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "Postal code must not be empty or consist only of whitespace")
        @Size(max = 255)
        String postalCode,

        @NotBlank(groups = Create.class, message = "City is required on create")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "City must not be empty or consist only of whitespace")
        @Size(max = 255)
        String city,

        @NotBlank(groups = Create.class, message = "Country is required on create")
        @Pattern(regexp = "\\S[\\S\\s]*", groups = Update.class,
                message = "Country must not be empty or consist only of whitespace")
        @Size(max = 255)
        String country,

        @NotNull(groups = Create.class, message = "Address type is required on create")
        AddressType addressType
) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}
