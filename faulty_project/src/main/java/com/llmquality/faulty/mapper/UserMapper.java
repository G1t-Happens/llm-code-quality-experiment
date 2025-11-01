package com.llmquality.faulty.mapper;

import com.llmquality.faulty.dto.UserRequest;
import com.llmquality.faulty.dto.UserResponse;
import com.llmquality.faulty.entity.User;
import org.mapstruct.*;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Mapper interface for converting between database entity {@link User} and User DTOs.
 */
@Mapper(componentModel = "spring")
public interface UserMapper {

    /**
     * Maps a {@link UserRequest} to a {@link User} entity.
     * The {@code id} is ignored since it is managed by JPA/database.
     * The password is hashed using the provided {@link PasswordEncoder}.
     *
     * @param dto             the DTO to map
     * @param passwordEncoder the password encoder to hash the password
     * @return the mapped User entity with hashed password
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "password", expression = "java(passwordEncoder.encode(dto.getPassword()))")
    User toUserEntity(UserRequest dto, @Context PasswordEncoder passwordEncoder);

    /**
     * Maps a {@link User} entity to a {@link UserResponse}.
     *
     * @param user the entity to map
     * @return the DTO representing the user without sensitive data
     */
    UserResponse toUserResponse(User user);


    /**
     * Updates the fields of the given {@link User} entity using values from the provided {@link UserRequest} DTO.
     * <p>
     * The method will map the following fields:
     * <ul>
     *     <li> {@code id} is ignored (not mapped) </li>
     *     <li> {@code name}, {@code email}, {@code password}, and {@code admin} are mapped from the DTO to the entity,
     *          with any {@code null} values being ignored. </li>
     * </ul>
     *
     * @param dto    the {@link UserRequest} DTO containing the data to update the entity.
     * @param entity the {@link User} entity to be updated.
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "name", source = "name", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "email", source = "email", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "password", source = "password", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "admin", source = "admin", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateUserEntityFromUserRequest(UserRequest dto, @MappingTarget User entity);
}
