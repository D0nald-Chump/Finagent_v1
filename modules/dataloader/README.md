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

### Example usage
```python
from dataloader import get_four_statements

frames = get_four_statements(
    ticker="TSLA",
    user_agent="FinAgents/1.0 (contact: you@example.com)"
)
print(frames["BS"].head())
```

### Notes
- Set a real **User-Agent** (with contact) to follow SEC fair‑use guidance.
- Live integration test is **opt-in**: set `SEC_UA` env var to run it: `SEC_UA="..." pytest -k integration`.
- By default, we filter to consolidated (no segment axes) and USD/pure units.
```

---

## LICENSE

MIT License

Copyright (c) 2025 FinAgents

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
