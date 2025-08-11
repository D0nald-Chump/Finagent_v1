# Finagent v1

Modular LangGraph-based financial report agent with token-cost tracking.

## Setup

1. Python 3.10+
2. Install deps:

```bash
pip install -r requirements.txt
```

3. Set OpenAI key (or compatible):

- Preferred: copy `.env.example` to `.env` and edit your own key

```powershell
Copy-Item .env.example .env
notepad .env
```

or macOS/Linux:

```bash
cp .env.example .env
nano .env
```

- Alternatively, set environment variable directly (no .env file needed):

Windows PowerShell (current session):

```powershell
$env:OPENAI_API_KEY="sk-..."
```

macOS/Linux (current session):

```bash
export OPENAI_API_KEY="sk-..."
```

Windows persistent:

```powershell
setx OPENAI_API_KEY "sk-..."
```

## Run

```bash
python main.py
```

This will run the pipeline and generate `main.ipynb` reproducing the run.

## Project Layout

- finagent/
  - config.py: model name and pricing
  - tokens.py: token counting
  - costing.py: cost logging utilities
  - prompts.py: all LLM prompts
  - state.py: shared state, reducers, helpers
  - nodes.py: all graph nodes (workers, checkers, aggregator)
  - graph.py: subgraph and parent graph assembly
- main.py: CLI entry that runs pipeline and exports a notebook
- requirements.txt
- README.md

## Notes

- If OpenAI SDK is unavailable, code falls back to stub outputs and approximate token count.
- The checker nodes include a guard to set `passed=True` at max retries to avoid infinite join waits.

## Security

- Do not commit `.env` or any secrets. `.gitignore` already ignores `.env`/`*.env`.
- If a key was accidentally committed, rotate it immediately and consider cleaning git history (BFG or `git filter-repo`).

