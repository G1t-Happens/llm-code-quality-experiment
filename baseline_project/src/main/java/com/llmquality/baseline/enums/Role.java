package com.llmquality.baseline.enums;


/**
 * Enum representing the roles available in the application.
 * Each role is associated with a string value used for
 * authorization and security purposes.
 *
 * <p>
 * Available roles:
 * <ul>
 *     <li>ADMIN - Represents an administrator with full access (ROLE_ADMIN)</li>
 *     <li>USER  - Represents a standard user with limited access (ROLE_USER)</li>
 * </ul>
 * </p>
 */
public enum Role {
    ADMIN("ROLE_ADMIN"),
    USER("ROLE_USER");

    private final String name;

    Role(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}