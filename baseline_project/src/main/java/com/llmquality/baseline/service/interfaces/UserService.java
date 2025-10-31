package com.llmquality.baseline.service.interfaces;

import com.llmquality.baseline.dto.LoginRequest;
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
     * Validates the login credentials provided in the {@link LoginRequest}.
     * <p>
     * Checks if a user with the given username exists and whether the
     * provided password matches the stored password.
     * </p>
     *
     * @param loginRequest the login request containing username and password; must not be {@code null}
     * @return {@code true} if the login is successful (username exists and password matches),
     * {@code false} otherwise
     */
    boolean checkLogin(LoginRequest loginRequest);
}
