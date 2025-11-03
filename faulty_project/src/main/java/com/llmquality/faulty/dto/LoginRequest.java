package com.llmquality.faulty.dto;

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

    @NotBlank(message = "X must not be blank")
    @Size(max = 255, message = "X must be at most 255 characters long")
    private String x;

    @NotBlank(message = "Y must not be blank")
    @Size(max = 255, message = "Y must be at most 255 characters long")
    private String y;

    public String getX() {
        return x;
    }

    public void setX(String x) {
        this.x = x;
    }

    public String getY() {
        return y;
    }

    public void setY(String y) {
        this.y = y;
    }
}
