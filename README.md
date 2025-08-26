# Finagent v1

Modular LangGraph-based financial report agent with token-cost tracking.

## Setup

1. Python 3.12+
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

Install deps (once):

```bash
pip install -r requirements.txt
```

Run with a specific PDF (recommended):

```bash
python main.py --pdf TSLA-Q2-2025-Update.pdf
```

If `--pdf` is omitted, the app will try to use `TSLA-Q2-2025-Update.pdf` in the repo root if present; otherwise it falls back to a small dummy stub text. The run will also generate `main.ipynb` reproducing the run.

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

## Financial Statements Retrival

### Example Usage
```python
from runtime_libs.finagents_common.financial_statements_retriever import FinancialStatementsRetriever

pd_is = FinancialStatementsRetriever("TSLA", cik="", sec_api_key="", mode="offline").fetch("20250630", "IS")
print(pd_is)
```

## Notes

- If OpenAI SDK is unavailable, code falls back to stub outputs and approximate token count.
- The checker nodes include a guard to set `passed=True` at max retries to avoid infinite join waits.

## Security

- Do not commit `.env` or any secrets. `.gitignore` already ignores `.env`/`*.env`.
- If a key was accidentally committed, rotate it immediately and consider cleaning git history (BFG or `git filter-repo`).

