import json
from pathlib import Path
from sec_api import ExtractorApi, XbrlApi

from financial_statements import OFFLINE_DATA_FOLDER, SEC_API_KEY
from sec import download_10q_between

ticker = "TSLA"
cik_padded = "0001318605"

# sec_extractor = ExtractorApi(sec_api_key)
# url_tsla_10_q = 'https://www.sec.gov/Archives/edgar/data/1318605/000162828025035806/tsla-20250630.htm'
# tsla_financial_statements = sec_extractor.get_section(url_tsla_10_q, 'part1item1', 'html')
# print(tsla_financial_statements)
#
# # Write text into a file (overwrites if file exists)
# with open("../data/tsla/sec_api/tsla_20250630_financial_statements.html", "w", encoding="utf-8") as f:
#     f.write(tsla_financial_statements)

xbrlApi = XbrlApi(SEC_API_KEY)

paths = download_10q_between(ticker, "2024-08-10", "2025-04-10", cik_padded, OFFLINE_DATA_FOLDER / f"{ticker.lower()}/10q")

for path, url_path in paths:
    p = Path(path)
    # Get the stem (filename without extension): "tsla-20250630"
    stem = p.stem  # 'tsla-20250630'
    # Replace "-" with "_" and add suffix
    filename = stem.replace("-", "_") + "_financial_statements.json"

    out_path = OFFLINE_DATA_FOLDER / f"{ticker.lower()}/sec_api/{filename}"

    print(f"Downloading {out_path}")

    xbrl_json = xbrlApi.xbrl_to_json(htm_url=url_path)

    # Write text into a file (overwrites if file exists)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(xbrl_json, f, ensure_ascii=False, indent=2)
