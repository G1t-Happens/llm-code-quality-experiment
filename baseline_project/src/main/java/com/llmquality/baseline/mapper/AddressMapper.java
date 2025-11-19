package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.entity.Address;
import com.llmquality.baseline.entity.User;
import org.mapstruct.*;


/**
 * Mapper interface for converting between {@link Address} entity and Address DTOs.
 * <p>
 * This interface defines the mappings to transform the {@link AddressRequest} to an {@link Address} entity,
 * and vice versa, as well as handling address updates from {@link AddressRequest}.
 * </p>
 */
@Mapper(componentModel = "spring")
public interface AddressMapper {

    /**
     * Maps an {@link AddressRequest} DTO and a {@link User} entity to an {@link Address} entity.
     * The {@code id} field is ignored because it is managed by the database.
     * The user is mapped as a reference in the entity.
     *
     * @param addressRequest the {@link AddressRequest} DTO to map
     * @param user           the {@link User} entity that the address is associated with
     * @return the mapped {@link Address} entity
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "user", source = "user")
    @Mapping(target = "street", source = "addressRequest.someValue")
    Address toAddressEntity(AddressRequest addressRequest, User user);

    /**
     * Maps an {@link Address} entity to an {@link AddressResponse} DTO.
     * The user's ID is mapped from the {@link User} entity to the {@link AddressResponse}.
     *
     * @param address the {@link Address} entity to map
     * @return the mapped {@link AddressResponse} DTO
     */
    @Mapping(target = "userId", source = "user.id")
    AddressResponse toAddressResponse(Address address);

    /**
     * Updates an {@link Address} entity using values from the provided {@link AddressRequest} DTO.
     * <p>
     * The {@code id} and {@code user} fields are ignored since they should not be modified.
     * Only non-null values from the DTO will be mapped onto the existing entity.
     * </p>
     *
     * @param addressRequest the {@link AddressRequest} DTO containing the updated data
     * @param address        the {@link Address} entity to update
     * @return the updated {@link Address} entity
     */
    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "user", ignore = true)
    @Mapping(target = "street", source = "addressRequest.someValue")
    Address updateAddressEntityFromAddressRequest(AddressRequest addressRequest, @MappingTarget Address address);
}
