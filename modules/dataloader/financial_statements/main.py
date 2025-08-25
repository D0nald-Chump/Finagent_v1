from sec_api import ExtractorApi

from financial_statements import OFFLINE_DATA_FOLDER
from sec import download_10q_between

ticker = "TSLA"
cik_padded = "0001318605"

sec_api_key = '5108ca782f64e3e749288cf55cf15c77a3426e0da85b3cbab1169c51f7f4d4c5'

# frames = get_four_statements(ticker, cik, out_dir='data/raw')
url_tsla_10_q = 'https://www.sec.gov/Archives/edgar/data/1318605/000162828025035806/tsla-20250630.htm'

# sec_extractor = ExtractorApi(sec_api_key)
# tsla_financial_statements = sec_extractor.get_section(url_tsla_10_q, 'part1item1', 'html')
# print(tsla_financial_statements)
#
# # Write text into a file (overwrites if file exists)
# with open("../data/tsla/sec_api/tsla_20250630_financial_statements.html", "w", encoding="utf-8") as f:
#     f.write(tsla_financial_statements)


download_10q_between(ticker, "2024-08-10", "2025-08-10", cik_padded, OFFLINE_DATA_FOLDER / f"{ticker.lower()}/10q")

