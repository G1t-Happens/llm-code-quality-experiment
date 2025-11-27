package com.llmquality.baseline.dto.validation;


/**
 * This class contains a validation group for differentiating between the
 * validation rules applied during the creation and update of a user.
 * <p>
 * These groups are used to apply specific validation constraints based on
 * the operation (create or update) being performed.
 * </p>
 *
 * <p>
 * The purpose of validation groups is to control which validation rules
 * are applied depending on the context, preventing unnecessary validations
 * for operations that don’t require them e.q. update requests
 * </p>
 */
public final class UserValidationGroups {

    /**
     * Private constructor to prevent instantiation of this utility class.
     * Throws UnsupportedOperationException if called.
     */
    private UserValidationGroups() {
        throw new UnsupportedOperationException("Utility class - should not be instantiated");
    }

    /**
     * Validation group for creating a new user.
     * <p>
     * This interface is used to mark the validation constraints that should
     * be applied when creating a new user (e.g., during user registration).
     * </p>
     */
    public interface Create {
    }

    /**
     * Validation group for updating an existing user.
     * <p>
     * This interface is used to mark the validation constraints that should
     * be applied when updating a user.
     * </p>
     */
    public interface Update {
    }
}
