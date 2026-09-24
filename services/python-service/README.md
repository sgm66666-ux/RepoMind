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

For the local Agent workflow, set `REPOMIND_LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, and `OLLAMA_MODEL=qwen2.5-coder:14b`, and ensure Ollama is running with that model installed. Without a configured LLM provider, Agent requests return an explicit 503; deterministic code analysis remains available.
