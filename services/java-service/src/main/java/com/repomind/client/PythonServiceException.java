package com.repomind.client;

public class PythonServiceException extends RuntimeException {
    private final int status;

    public PythonServiceException(String message, int status) {
        super(message);
        this.status = status;
    }

    public int status() {
        return status;
    }
}
