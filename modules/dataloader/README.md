# Financial Statements Data Loader

A tiny library that downloads the latest **10-Q** for a ticker, parses XBRL with **Arelle**, and
reconstructs **BS, IS, CF, SE** directly from the **presentation roles** (includes both `us-gaap:*`
 and company extension tags).

## Quick Start

### Build ENV
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt 
```

### 🔑 Local Configuration

This project requires an API key for accessing sec_api parsing service. To keep secrets out of version control,
we use a hidden config file in `.dataloader_config`. This file is already included in `.gitignore`,
so it will never be committed.

Simply create a file at:
`dataloader/`
and add your keys in `KEY=VALUE` format, one per line. For example:
```ini
sec_api_key=${YOUR_SEC_API_KEY}
```


### Example usage
```python
# WIP



```

### Notes
- Set a real **User-Agent** (with contact) to follow SEC fair‑use guidance.
- Live integration test is **opt-in**: set `SEC_UA` env var to run it: `SEC_UA="..." pytest -k integration`.
- By default, we filter to consolidated (no segment axes) and USD/pure units.
```
