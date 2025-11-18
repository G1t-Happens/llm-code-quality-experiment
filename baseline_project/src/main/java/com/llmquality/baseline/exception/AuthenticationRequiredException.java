package com.llmquality.baseline.exception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.io.Serial;
import java.io.Serializable;

/**
 * Exception thrown when an operation requires an authenticated user, but the current request is not authenticated.
 * <p>
 * This exception results in a 401 Unauthorized response and follows the same pattern as other resource-related
 * exceptions in the application.
 * </p>
 *
 * <p>Example usage:</p>
 * <pre>
 * throw new AuthenticationRequiredException("User", "authentication", "none");
 * </pre>
 */
@ResponseStatus(value = HttpStatus.UNAUTHORIZED)
public class AuthenticationRequiredException extends BaselineProjectWebException {

    @Serial
    private static final long serialVersionUID = 6843019275638472910L;

    /**
     * Constructs a new AuthenticationRequiredException with fixed values matching the pattern of other exceptions.
     * <p>
     * Message format: "User not authenticated with authentication : 'none'"
     * </p>
     *
     * @param resourceName always "User"
     * @param fieldName    always "authentication"
     * @param fieldValue   always "none" (or any descriptive value like "expired", "missing")
     */
    public AuthenticationRequiredException(String resourceName, String fieldName, Serializable fieldValue) {
        super("not authenticated with", resourceName, fieldName, fieldValue);
    }
}