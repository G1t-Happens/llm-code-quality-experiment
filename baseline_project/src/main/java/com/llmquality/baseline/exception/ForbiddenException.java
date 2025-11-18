package com.llmquality.baseline.exception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.io.Serial;
import java.io.Serializable;


/**
 * Exception thrown when a user does not have permission to access a resource.
 * <p>
 * This exception is typically used when a user attempts to perform an action on a resource
 * for which they do not have the necessary authorization or permissions.
 * It returns a 403 Forbidden HTTP status to indicate that the server understood the request,
 * but refuses to authorize it.
 * </p>
 *
 * <p>Example usage:</p>
 * <pre>
 * throw new ForbiddenException("User", "id", userId);
 * </pre>
 */
@ResponseStatus(value = HttpStatus.FORBIDDEN)
public class ForbiddenException extends BaselineProjectWebException {

    @Serial
    private static final long serialVersionUID = 1234567890123456789L;

    /**
     * Constructs a new ForbiddenException with a specified resource name, field name, and field value.
     * <p>
     * The exception message is formatted as "forbidden" for the given resource and field.
     * </p>
     *
     * @param resourceName the name of the resource that the exception relates to (e.g., "User", "Product")
     * @param fieldName    the name of the field that caused the exception (e.g., "id", "role")
     * @param fieldValue   the value of the field that caused the exception (e.g., userId, roleName)
     */
    public ForbiddenException(String resourceName, String fieldName, Serializable fieldValue) {
        super("access forbidden for", resourceName, fieldName, fieldValue);
    }
}
