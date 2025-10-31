package com.llmquality.faulty.exception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.io.Serial;
import java.io.Serializable;


/**
 * Exception thrown when an attempt is made to create or modify a resource that already exists.
 * <p>
 * This exception is typically used when an attempt is made to create a resource (e.g., user, product) with
 * a unique field (e.g., email, username) that already exists in the system, violating the uniqueness constraint.
 * It returns a 409 Conflict HTTP status to indicate a conflict in the request due to existing data.
 * </p>
 *
 * <p>Example usage:</p>
 * <pre>
 * throw new ResourceAlreadyExistsException("User", "email", "test@example.com");
 * </pre>
 */
@ResponseStatus(value = HttpStatus.CONFLICT)
public class ResourceAlreadyExistsException extends BaselineProjectWebException {

    @Serial
    private static final long serialVersionUID = 2978506968943653610L;

    /**
     * Constructs a new ResourceAlreadyExistsException with a specified resource name, field name, and field value.
     * <p>
     * The exception message is formatted as "already exists" for the given resource and field.
     * </p>
     *
     * @param resourceName the name of the resource that the exception relates to (e.g., "User", "Product")
     * @param fieldName    the name of the field that caused the exception (e.g., "email", "username")
     * @param fieldValue   the value of the field that caused the exception (e.g., "test@example.com", "johndoe")
     */
    public ResourceAlreadyExistsException(String resourceName, String fieldName, Serializable fieldValue) {
        super("already exists", resourceName, fieldName, fieldValue);
    }
}
