package com.repomind.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.repomind.client.PythonServiceClient;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class RepoMindService {
    private final PythonServiceClient client;

    public RepoMindService(PythonServiceClient client) {
        this.client = client;
    }

    public JsonNode analyze(Map<String, Object> request) { return client.analyzeRepository(request); }
    public JsonNode symbols(Map<String, String> query) { return client.listSymbols(query); }
    public JsonNode symbol(String id) { return client.getSymbol(id); }
    public JsonNode callers(String id) { return client.callers(id); }
    public JsonNode callees(String id) { return client.callees(id); }
    public JsonNode callGraph(Map<String, String> query) { return client.callGraph(query); }
    public JsonNode readFile(Map<String, String> query) { return client.readFile(query); }
    public JsonNode context(Map<String, Object> request) { return client.context(request); }
    public JsonNode orderDemo() { return client.orderDemo(); }
    public JsonNode fault(Map<String, Object> request) { return client.faultLocalization(request); }
    public JsonNode agent(Map<String, Object> request) { return client.agentChat(request); }
}
