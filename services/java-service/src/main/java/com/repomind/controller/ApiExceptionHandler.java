package com.repomind.controller;

import com.repomind.client.PythonServiceException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(PythonServiceException.class)
    public ResponseEntity<Map<String, Object>> pythonService(PythonServiceException ex) {
        int status = ex.status() >= 400 && ex.status() < 600 ? ex.status() : 502;
        return ResponseEntity.status(status).body(Map.of("error", "PYTHON_SERVICE_ERROR", "message", ex.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> unexpected(Exception ex) {
        return ResponseEntity.internalServerError().body(Map.of("error", "INTERNAL_ERROR", "message", "Unexpected server error"));
    }
}
