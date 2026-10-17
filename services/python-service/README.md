# RepoMind Python Code Intelligence, Fault Localization and Agent Service

Requires Python 3.11 or newer. Install dependencies with `python -m pip install -r requirements.txt` in a fresh virtual environment.

The service implements the executable pipeline:

```text
Repository -> tree-sitter -> AST -> Symbols -> Relations -> Call Graph -> Context -> Tools -> Fault Localization
```

## Run tests

Use the project Python runtime or an activated virtual environment:

```powershell
python -m pytest -p no:cacheprovider -q
```

## Run the API

```powershell
python -m uvicorn app.main:app --reload
```

Then call `POST /analysis/repository` with an absolute path to a repository (the root-level `scripts/prepare-demo.ps1` resolves the bundled demo path for you).

Vue uses the same-origin Vite proxy and the compatible `/api` routes on this service; no Java gateway is required. For example, `POST /api/repositories/analyze` reuses the native analysis handler. Native endpoints keep their existing responses; browser errors keep `{error, message}`. `GET /api/health` returns `{status: "ok", service: "python-service"}`, while `GET /health` remains unchanged.

The default CORS allowlist is `http://localhost:5173,http://127.0.0.1:5173`. Override `REPOMIND_FRONTEND_ORIGINS` only when direct browser access needs other explicit origins. There is no authentication layer; keep this local trusted-user service bound to loopback. File reads still use the existing analyzed-repository boundary and Java/Python suffix checks.

For the local Agent workflow, set `REPOMIND_LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, and `OLLAMA_MODEL=qwen2.5-coder:14b`, and ensure Ollama is running with that model installed. Without a configured LLM provider, Agent requests return an explicit 503; deterministic code analysis remains available.
