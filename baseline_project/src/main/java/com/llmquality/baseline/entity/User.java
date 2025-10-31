package com.llmquality.baseline.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Size;

import java.util.Objects;


@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private long id = 0L;

    @Column(name = "username", nullable = false)
    @Size(max = 255)
    private String name;

    @Column(name = "userpw", nullable = false)
    @Size(max = 255)
    private String password;

    @Column(name = "email", nullable = false)
    @Size(max = 255)
    private String email;

    @Column(name = "isadmin", nullable = false)
    private boolean admin;

    public boolean isAdmin() {
        return admin;
    }

    public void setAdmin(boolean admin) {
        this.admin = admin;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof User user)) return false;
        return Objects.equals(name, user.getName());
    }

    @Override
    public int hashCode() {
        return name.hashCode();
    }
}
