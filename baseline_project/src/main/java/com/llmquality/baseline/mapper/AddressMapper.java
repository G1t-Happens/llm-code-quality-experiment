package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.entity.Address;
import com.llmquality.baseline.entity.User;
import org.mapstruct.*;


@Mapper(componentModel = "spring")
public interface AddressMapper {

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "user", source = "user")
    Address toAddressEntity(AddressRequest addressRequest, User user);

    @Mapping(target = "userId", source = "user.id")
    AddressResponse toAddressResponse(Address address);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "user", ignore = true)
    Address updateAddressEntityFromAddressRequest(@MappingTarget Address address, AddressRequest addressRequest);
}
