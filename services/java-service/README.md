# RepoMind Java Gateway

Requires JDK 21 and Maven. The required Java version is configured in `pom.xml`.

Spring Boot gateway for the Python intelligence service. It exposes `/api/health`, `/api/repositories/analyze`, `/api/symbols`, `/api/fault-localization`, and `/api/agent/chat`, and forwards requests through `PythonServiceClient`.

Configure `repomind.python-service-url` in `src/main/resources/application.yml`. Build and test with:

```powershell
mvn test
mvn spring-boot:run
```

The gateway does not implement a fake Agent. Agent execution remains in the Python service's independent `AgentLoop`.
