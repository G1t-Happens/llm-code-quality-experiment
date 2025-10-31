package com.llmquality.faulty.dto;

import com.llmquality.faulty.dto.validation.UserValidationGroups;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;


public class UserRequest {

    @NotBlank(groups = {UserValidationGroups.Create.class})
    private String name;

    @NotNull(groups = UserValidationGroups.Create.class)
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

