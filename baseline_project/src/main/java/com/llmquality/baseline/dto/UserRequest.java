package com.llmquality.baseline.dto;

import com.llmquality.baseline.dto.validation.UserValidationGroups;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;


/**
 * Data Transfer Object (DTO) for creating or updating a User.
 * <p>
 * Contains user input fields with validation annotations for create and update operations.
 * </p>
 */
public class UserRequest {

    @NotBlank(groups = {UserValidationGroups.Create.class})
    private String username;

    @NotBlank(groups = UserValidationGroups.Create.class)
    @Pattern(regexp = "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$",
            message = "Password must be at least 8 characters long, contain at least one number, one lowercase and one uppercase letter.",
            groups = {UserValidationGroups.Update.class, UserValidationGroups.Create.class}
    )
    private String password;

    @NotBlank(groups = UserValidationGroups.Create.class)
    @Email(groups = {UserValidationGroups.Update.class, UserValidationGroups.Create.class})
    private String email;

    @NotNull(groups = UserValidationGroups.Create.class)
    private Boolean admin;

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

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public Boolean getAdmin() {
        return admin;
    }

    public void setAdmin(Boolean admin) {
        this.admin = admin;
    }
}
