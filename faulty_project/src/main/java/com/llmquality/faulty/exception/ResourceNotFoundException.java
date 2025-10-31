package com.llmquality.faulty.exception;

import com.llmquality.faulty.exception.BaselineProjectWebException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.io.Serial;
import java.io.Serializable;


/**
 * Exception thrown when a requested resource is not found in the system.
 * <p>
 * This exception is used to indicate that a resource, such as an entity or data, could not be found based on
 * the specified field and value. It returns a 404 Not Found HTTP status code to indicate that the requested
 * resource does not exist.
 * </p>
 *
 * <p>Example usage:</p>
 * <pre>
 * throw new ResourceNotFoundException("User", "id", 123);
 * </pre>
 */
@ResponseStatus(value = HttpStatus.NOT_FOUND)
public class ResourceNotFoundException extends BaselineProjectWebException {

    @Serial
    private static final long serialVersionUID = 4703052950035630239L;

    /**
     * Constructs a new ResourceNotFoundException with a specified resource name, field name, and field value.
     * <p>
     * The exception message is formatted as "not found with" for the given resource and field.
     * </p>
     *
     * @param resourceName the name of the resource that could not be found (e.g., "User", "Product")
     * @param fieldName    the name of the field that was used to search for the resource (e.g., "id", "username")
     * @param fieldValue   the value of the field that was used to search for the resource (e.g., 123, "john_doe")
     */
    public ResourceNotFoundException(String resourceName, String fieldName, Serializable fieldValue) {
        super("not found with", resourceName, fieldName, fieldValue);
    }
}
