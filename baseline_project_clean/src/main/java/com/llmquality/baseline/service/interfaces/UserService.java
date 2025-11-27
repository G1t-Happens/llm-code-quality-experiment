package com.llmquality.baseline.service.interfaces;

import com.llmquality.baseline.dto.LoginRequest;
import com.llmquality.baseline.dto.LoginResponse;
import com.llmquality.baseline.dto.UserRequest;
import com.llmquality.baseline.dto.UserResponse;
import com.llmquality.baseline.entity.User;


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
     */
    LoginResponse checkLogin(LoginRequest loginRequest);

    /**
     * Retrieves a user by their username.
     *
     * @param username username the username to search for
     * @return the corresponding {@link UserResponse}
     */
    UserResponse getByUsername(String username);
}
