package com.llmquality.baseline.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;


public class LoginRequest {

    @NotBlank(message = "Name must not be blank")
    @Size(max = 255, message = "Name must be at most 255 characters long")
    private String name;

    @NotBlank(message = "Password must not be blank")
    @Size(max = 255, message = "Password must be at most 255 characters long")
    private String password;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}

