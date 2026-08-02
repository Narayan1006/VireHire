package com.verehire.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * Application-level exception that maps directly to an HTTP response.
 *
 * Usage:
 *   throw new ApiException(HttpStatus.NOT_FOUND, "Job not found: " + jobId);
 *   throw new ApiException(HttpStatus.CONFLICT, "Email already registered.");
 *
 * Handled globally by {@link GlobalExceptionHandler} which serializes
 * this into the standard error response JSON.
 */
public class ApiException extends RuntimeException {

    private final HttpStatus status;

    public ApiException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

    public ApiException(HttpStatus status, String message, Throwable cause) {
        super(message, cause);
        this.status = status;
    }

    public HttpStatus getStatus() {
        return status;
    }
}
