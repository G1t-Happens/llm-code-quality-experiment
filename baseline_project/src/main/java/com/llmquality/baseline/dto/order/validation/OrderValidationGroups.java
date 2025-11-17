package com.llmquality.baseline.dto.order.validation;


import jakarta.validation.groups.Default;

/**
 * This class contains a validation group for differentiating between the
 * validation rules applied during the creation and update of a order.
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
public final class OrderValidationGroups {

    /**
     * Private constructor to prevent instantiation of this utility class.
     * Throws UnsupportedOperationException if called.
     */
    private OrderValidationGroups() {
        throw new UnsupportedOperationException("Utility class");
    }

    /**
     * Validation group for creating a new order.
     * <p>
     * This interface is used to mark the validation constraints that should
     * be applied when creating a new order (e.g., during order registration).
     * </p>
     */
    public interface Create extends Default {
    }

    /**
     * Validation group for updating an existing order.
     * <p>
     * This interface is used to mark the validation constraints that should
     * be applied when updating an order.
     * </p>
     */
    public interface Update {
    }
}
