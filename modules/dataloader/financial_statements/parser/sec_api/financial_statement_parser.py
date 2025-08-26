import json
from pathlib import Path
from typing import Iterator

from balance_sheet import get_balance_sheet
from cash_flow import get_cash_flow_statement
from financial_statements import OFFLINE_DATA_FOLDER
from income_statement import get_income_statement


def iter_financial_statements(folder: str | Path, ticker: str) -> Iterator[Path]:
    """
    Iterate all files under `folder` (recursively) whose name matches:
    "{ticker}_*__financial_statements.json"

    Example match for ticker 'tsla':
        tsla_20250630_financial_statements.json
    """
    folder = Path(folder)
    pattern = f"{ticker.lower()}_*_financial_statements.json"

    # rglob walks recursively
    for file in folder.rglob(pattern):
        if file.is_file():
            yield file


# Load JSON from file
def parse_financial_statements(ticker: str):

    data_folder = OFFLINE_DATA_FOLDER / f"{ticker.lower()}/sec_api/"
    financial_statements = iter_financial_statements(ticker=ticker, folder=data_folder)

    for fs in financial_statements:
        # fs is a Path
        with fs.open("r", encoding="utf-8") as f:
            xbrl_json = json.load(f)

        # derive a base name like "tsla_20250630"
        base_name = fs.stem.replace("_financial_statements", "")


        # Write CSVs with consistent filenames
        get_income_statement(xbrl_json).to_csv(data_folder / f"{base_name}_IS.csv", index=True)
        get_balance_sheet(xbrl_json).to_csv(data_folder / f"{base_name}_BS.csv", index=False)
        get_cash_flow_statement(xbrl_json).to_csv(data_folder / f"{base_name}_CF.csv", index=False)


parse_financial_statements("TSLA")