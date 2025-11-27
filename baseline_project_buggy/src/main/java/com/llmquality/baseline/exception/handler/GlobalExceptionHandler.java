package com.llmquality.baseline.exception.handler;

import com.llmquality.baseline.exception.BaselineProjectWebException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.List;


/**
 * Global exception handler that converts domain-specific and validation-related
 * exceptions into clean and consistent API error responses.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BaselineProjectWebException.class)
    public ResponseEntity<ErrorResponse> handleBaselineException(final BaselineProjectWebException ex) {
        final ResponseStatus annotation = ex.getClass().getAnnotation(ResponseStatus.class);
        final HttpStatus httpStatus = (annotation != null) ? annotation.value() : HttpStatus.INTERNAL_SERVER_ERROR;
        return ResponseEntity.status(httpStatus)
                .body(new ErrorResponse(
                        httpStatus.value(),
                        ex.getMessage()
                ));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ValidationErrorResponse> handleValidation(final MethodArgumentNotValidException ex) {
        final List<ValidationErrorResponse.FieldError> errors =
                ex.getBindingResult().getFieldErrors()
                        .stream()
                        .map(err -> new ValidationErrorResponse.FieldError(
                                err.getField(),
                                err.getRejectedValue(),
                                err.getDefaultMessage()
                        ))
                        .toList();
        return ResponseEntity.badRequest().body(new ValidationErrorResponse(400, "Validation failed", errors));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleMalformedJson(final HttpMessageNotReadableException ex) {
        return ResponseEntity.badRequest().body(new ErrorResponse(HttpStatus.BAD_REQUEST.value(),
                "Malformed JSON request: " + ex.getMostSpecificCause().getMessage()));
    }


    // Response Records
    public record ErrorResponse(int status, String message) {
    }

    public record ValidationErrorResponse(int status, String message, List<FieldError> errors) {
        public record FieldError(String field, Object rejectedValue, String message) {
        }
    }
}
