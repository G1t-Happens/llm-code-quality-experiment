package com.llmquality.baseline.exception;

import java.io.Serial;
import java.io.Serializable;


/**
 * Abstract base class for custom exceptions used in the BaselineProject.
 * <p>
 * This class serves as the base for exceptions related to resource validation and error handling in the backend.
 * It holds information about the resource, field, and field value that caused the exception to be thrown.
 * Subclasses of this class should provide specific exception messages and behaviors.
 * </p>
 *
 * <p>Example:</p>
 * <pre>
 * throw new ResourceNotFoundException("not found", "User", "id", userId);
 * </pre>
 *
 * @see ResourceNotFoundException
 * @see ResourceAlreadyExistsException
 */
public abstract class BaselineProjectWebException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = -2713300573235999908L;

    /**
     * Constructs a new BackendWebException with the specified message and details.
     * <p>
     * The message is formatted to include the resource name, message, field name, and field value.
     * </p>
     *
     * @param msg          the message to be included in the exception
     * @param resourceName the name of the resource
     * @param fieldName    the name of the field
     * @param fieldValue   the value of the field
     */
    protected BaselineProjectWebException(String msg, String resourceName, String fieldName, Serializable fieldValue) {
        super(String.format("%s %s %s : '%s'", resourceName, msg, fieldName, fieldValue));
    }
}
