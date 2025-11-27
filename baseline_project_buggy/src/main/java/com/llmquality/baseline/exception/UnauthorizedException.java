package com.llmquality.baseline.exception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

import java.io.Serial;
import java.io.Serializable;


/**
 * Thrown when authentication fails due to invalid username or password.
 * <p>
 * This exception is annotated with {@code @ResponseStatus(HttpStatus.UNAUTHORIZED)} and therefore
 * automatically returns HTTP 401 Unauthorized without any additional configuration.
 * </p>
 * <p>
 * It is the recommended way in modern Spring Boot 3+ REST APIs to handle failed login attempts.
 * Using this instead of returning {@code success: false} with 200 OK prevents information leakage
 * (username enumeration) and follows proper HTTP semantics.
 * </p>
 * <p>
 * Example usage:
 * <pre>
 * throw new UnauthorizedException("User", "username", username);
 * </pre>
 * </p>
 */
@ResponseStatus(value = HttpStatus.UNAUTHORIZED)
public class UnauthorizedException extends BaselineProjectWebException {

    @Serial
    private static final long serialVersionUID = -4368911695070591266L;

    /**
     * Constructs a new UnauthorizedException with details about the authentication failure.
     * <p>
     * The exception message is formatted as "access unauthorized for {resourceName} {fieldName} : '{fieldValue}'".
     * </p>
     *
     * @param resourceName the name of the resource that required authentication (e.g., "User")
     * @param fieldName    the name of the field that caused the failure (e.g., "username" or "credentials")
     * @param fieldValue   the value of the field that was invalid (e.g., the provided username)
     */
    public UnauthorizedException(String resourceName, String fieldName, Serializable fieldValue) {
        super("access unauthorized for", resourceName, fieldName, fieldValue);
    }
}
