package com.llmquality.baseline.dto.user;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;


/**
 * Data Transfer Object (DTO) for user login requests.
 * <p>
 * Contains the username and password fields with validation constraints
 * to ensure non-blank input and enforce maximum length.
 * </p>
 */
public class LoginRequest {

    @NotBlank(message = "Name must not be blank")
    @Size(max = 255, message = "Name must be at most 255 characters long")
    private String username;

    @NotBlank(message = "Password must not be blank")
    @Size(max = 255, message = "Password must be at most 255 characters long")
    private String password;

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}
