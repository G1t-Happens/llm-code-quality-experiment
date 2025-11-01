package com.llmquality.faulty.service.interfaces;

import com.llmquality.faulty.dto.LoginRequest;
import com.llmquality.faulty.dto.LoginResponse;
import com.llmquality.faulty.dto.UserRequest;
import com.llmquality.faulty.dto.UserResponse;
import com.llmquality.faulty.entity.User;
import com.llmquality.faulty.exception.ResourceNotFoundException;


/**
 * Service interface for managing {@link User} entities and performing
 * user-related operations such as authentication and lookup.
 * <p>
 * Extends {@link CRUDable} to provide standard Create, Read, Update,
 * and Delete operations for {@link UserResponse}/{@link User} objects.
 * </p>
 */
public interface UserService extends CRUDable<UserRequest, UserResponse> {

    /**
     * Validates user credentials and returns the login result.
     *
     * @param loginRequest the login request containing username and password
     * @return a {@link LoginResponse} indicating whether authentication was successful
     * @throws ResourceNotFoundException if the user with the given name does not exist
     */
    LoginResponse checkLogin(LoginRequest loginRequest) throws ResourceNotFoundException;
}
