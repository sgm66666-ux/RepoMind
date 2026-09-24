# Third-party dependencies

RepoMind uses these projects as package dependencies. No source code from ast-grep, Joern, SCIP or PyCG is copied into the repository.

| Project | Use | License | Upstream |
|---|---|---|---|
| tree-sitter | Parser runtime used by the Python analysis service | MIT | https://github.com/tree-sitter/tree-sitter |
| tree-sitter-java | Java grammar | MIT | https://github.com/tree-sitter/tree-sitter-java |
| tree-sitter-python | Python grammar | MIT | https://github.com/tree-sitter/tree-sitter-python |
| FastAPI | Python HTTP service | MIT | https://github.com/fastapi/fastapi |
| Spring Boot | Java HTTP service | Apache-2.0 | https://github.com/spring-projects/spring-boot |

The tree-sitter, tree-sitter-java, and tree-sitter-python licenses and copyright notices remain available from their upstream distributions. Versions are pinned by the service dependency constraints and should be locked before a public release.
