package com.repomind.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@Component
public class PythonServiceClient {
    private final RestClient client;
    private final ObjectMapper objectMapper;

    public PythonServiceClient(@Value("${repomind.python-service-url}") String baseUrl, ObjectMapper objectMapper) {
        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(new SimpleClientHttpRequestFactory())
                .build();
        this.objectMapper = objectMapper;
    }

    public JsonNode analyzeRepository(Map<String, Object> request) {
        return post("/analysis/repository", request);
    }

    public JsonNode listSymbols(Map<String, String> query) {
        return get("/symbols", query);
    }

    public JsonNode getSymbol(String id) {
        return get("/symbols/" + id, Map.of());
    }

    public JsonNode callers(String id) {
        return get("/symbols/" + id + "/callers", Map.of());
    }

    public JsonNode callees(String id) {
        return get("/symbols/" + id + "/callees", Map.of());
    }

    public JsonNode callGraph(Map<String, String> query) {
        return get("/call-graph", query);
    }

    public JsonNode readFile(Map<String, String> query) {
        return get("/files/read", query);
    }

    public JsonNode context(Map<String, Object> request) {
        return post("/context", request);
    }

    public JsonNode orderDemo() {
        return get("/demo/order-demo", Map.of());
    }

    public JsonNode faultLocalization(Map<String, Object> request) {
        return post("/fault-localization", request);
    }

    public JsonNode agentChat(Map<String, Object> request) {
        return post("/agent/chat", request);
    }

    private JsonNode get(String path, Map<String, String> query) {
        try {
            RestClient.RequestHeadersUriSpec<?> request = client.get();
            RestClient.RequestHeadersSpec<?> withQuery = request.uri(uriBuilder -> {
                var builder = uriBuilder.path(path);
                query.forEach(builder::queryParam);
                return builder.build();
            });
            return withQuery.accept(MediaType.APPLICATION_JSON).retrieve().onStatus(HttpStatusCode::isError, (req, response) -> throwServiceError(response)).body(JsonNode.class);
        } catch (PythonServiceException ex) {
            throw ex;
        } catch (RestClientException ex) {
            throw new PythonServiceException("Python service is unavailable", 503);
        }
    }

    private JsonNode post(String path, Map<String, Object> body) {
        try {
            return client.post().uri(path).contentType(MediaType.APPLICATION_JSON).accept(MediaType.APPLICATION_JSON).body(body).retrieve().onStatus(HttpStatusCode::isError, (req, response) -> throwServiceError(response)).body(JsonNode.class);
        } catch (PythonServiceException ex) {
            throw ex;
        } catch (RestClientException ex) {
            throw new PythonServiceException("Python service is unavailable", 503);
        }
    }

    private void throwServiceError(org.springframework.http.client.ClientHttpResponse response) throws IOException {
        String body = new String(response.getBody().readAllBytes(), StandardCharsets.UTF_8);
        String message = "Python service returned " + response.getStatusCode();
        if (!body.isBlank()) {
            try {
                JsonNode error = objectMapper.readTree(body);
                if (error.hasNonNull("detail")) {
                    JsonNode detail = error.get("detail");
                    message = detail.isTextual() ? detail.asText() : detail.toString();
                }
            } catch (IOException ignored) {
                message = body;
            }
        }
        throw new PythonServiceException(message, response.getStatusCode().value());
    }
}
