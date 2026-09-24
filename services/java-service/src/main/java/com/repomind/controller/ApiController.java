package com.repomind.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.repomind.service.RepoMindService;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class ApiController {
    private final RepoMindService service;

    public ApiController(RepoMindService service) {
        this.service = service;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "java-service");
    }

    @PostMapping("/repositories/analyze")
    public JsonNode analyze(@RequestBody Map<String, Object> request) { return service.analyze(request); }

    @GetMapping("/symbols")
    public JsonNode symbols(@RequestParam Map<String, String> query) { return service.symbols(query); }

    @GetMapping("/symbols/{id:.+}/callers")
    public JsonNode callers(@PathVariable String id) { return service.callers(id); }

    @GetMapping("/symbols/{id:.+}/callees")
    public JsonNode callees(@PathVariable String id) { return service.callees(id); }

    @GetMapping("/symbols/{id:.+}")
    public JsonNode symbol(@PathVariable String id) { return service.symbol(id); }

    @GetMapping("/call-graph")
    public JsonNode callGraph(@RequestParam Map<String, String> query) { return service.callGraph(query); }

    @GetMapping("/files/read")
    public JsonNode readFile(@RequestParam Map<String, String> query) { return service.readFile(query); }

    @PostMapping("/context")
    public JsonNode context(@RequestBody Map<String, Object> request) { return service.context(request); }

    @GetMapping("/demo/order-demo")
    public JsonNode orderDemo() { return service.orderDemo(); }

    @PostMapping("/fault-localization")
    public JsonNode fault(@RequestBody Map<String, Object> request) { return service.fault(request); }

    @PostMapping("/agent/chat")
    public JsonNode agent(@RequestBody Map<String, Object> request) { return service.agent(request); }
}
