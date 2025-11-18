package com.llmquality.baseline.dto;

import com.llmquality.baseline.dto.validation.AddressValidationGroups;
import com.llmquality.baseline.enums.AddressType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;


public record AddressRequest(
        @NotBlank(groups = AddressValidationGroups.Create.class)
        String street,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        String houseNumber,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        String postalCode,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        String city,

        @NotBlank(groups = AddressValidationGroups.Create.class)
        String country,

        @NotNull(groups = AddressValidationGroups.Create.class)
        AddressType addressType
) {
    // You can add custom methods here if needed, e.g., formatted output or convenience methods.
}