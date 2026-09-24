package com.repomind.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.repomind.client.PythonServiceException;
import com.repomind.service.RepoMindService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ApiController.class)
class ApiControllerTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper objectMapper;
    @MockBean RepoMindService service;

    @Test
    void healthIsAvailable() throws Exception {
        mvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void pythonServiceFailuresBecomeStructuredErrors() throws Exception {
        when(service.analyze(any())).thenThrow(new PythonServiceException("Python service is unavailable", 503));
        mvc.perform(post("/api/repositories/analyze")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("path", "demo"))))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.error").value("PYTHON_SERVICE_ERROR"));
    }

    @Test
    void callGraphIsForwardedWithoutInventingRelations() throws Exception {
        when(service.callGraph(any())).thenReturn(objectMapper.readTree("""
                {"nodes":[],"edges":[],"resolvedCallCount":0,"unresolvedCallCount":0}
                """));
        mvc.perform(get("/api/call-graph").param("includeUnresolved", "false"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.resolvedCallCount").value(0))
                .andExpect(jsonPath("$.edges").isArray());
    }

    @Test
    void realDemoAssetMetadataIsForwarded() throws Exception {
        when(service.orderDemo()).thenReturn(objectMapper.readTree("""
                {"repositoryPath":"D:/RepoMind/demo/order-demo","stackTrace":"InventoryService.java:12"}
                """));
        mvc.perform(get("/api/demo/order-demo"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.repositoryPath").value("D:/RepoMind/demo/order-demo"))
                .andExpect(jsonPath("$.stackTrace").value("InventoryService.java:12"));
    }
}
