import json

import pandas as pd
from sec_api import XbrlApi
from financial_statements import OFFLINE_DATA_FOLDER
from income_statement import get_income_statement
from income_statement_with_segment import build_income_statement_with_segments

print("Offline folder is:", OFFLINE_DATA_FOLDER)

SEC_API_KEY = "5108ca782f64e3e749288cf55cf15c77a3426e0da85b3cbab1169c51f7f4d4c5"


# convert XBRL-JSON of balance sheet to pandas dataframe
def get_balance_sheet(xbrl_json):
    balance_sheet_store = {}

    for usGaapItem in xbrl_json['BalanceSheets']:
        values = []
        indicies = []

        for fact in xbrl_json['BalanceSheets'][usGaapItem]:
            # only consider items without segment.
            if 'segment' not in fact:
                index = fact['period']['instant']

                # avoid duplicate indicies with same values
                if index in indicies:
                    continue

                # add 0 if value is nil
                if "value" not in fact:
                    values.append(0)
                else:
                    values.append(fact['value'])

                indicies.append(index)

            balance_sheet_store[usGaapItem] = pd.Series(values, index=indicies)

    balance_sheet = pd.DataFrame(balance_sheet_store)
    # switch columns and rows so that US GAAP items are rows and each column header represents a date instant
    return balance_sheet.T


def get_cash_flow_statement(xbrl_json):
    cash_flows_store = {}

    for usGaapItem in xbrl_json['StatementsOfCashFlows']:
        values = []
        indicies = []

        for fact in xbrl_json['StatementsOfCashFlows'][usGaapItem]:
            # only consider items without segment.
            if 'segment' not in fact:
                # check if date instant or date range is present
                if "instant" in fact['period']:
                    index = fact['period']['instant']
                else:
                    index = fact['period']['startDate'] + '-' + fact['period']['endDate']

                # avoid duplicate indicies with same values
                if index in indicies:
                    continue

                if "value" not in fact:
                    values.append(0)
                else:
                    values.append(fact['value'])

                indicies.append(index)

        cash_flows_store[usGaapItem] = pd.Series(values, index=indicies)

    cash_flows = pd.DataFrame(cash_flows_store)
    return cash_flows.T


# # 10-K HTM File URL example
# url_tsla_10_q = 'https://www.sec.gov/Archives/edgar/data/1318605/000162828025035806/tsla-20250630.htm'
# xbrl_json = xbrlApi.xbrl_to_json(htm_url=url_tsla_10_q)
#
# # Write text into a file (overwrites if file exists)
# with open("tsla_20250630_financial_statements.json", "w", encoding="utf-8") as f:
#     json.dump(xbrl_json, f, ensure_ascii=False, indent=2)

# Load JSON from file

with open(OFFLINE_DATA_FOLDER / "tsla/sec_api/tsla_20250630_financial_statements.json", "r", encoding="utf-8") as f:
    xbrl_json = json.load(f)

income_statement = get_income_statement(xbrl_json)
income_statement.to_csv("tsla_20250630_IS.csv", index=True)

income_statement_with_segments = build_income_statement_with_segments(xbrl_json)
income_statement_with_segments.to_csv("tsla_20250630_IS_w_segments.csv", index=True)

balance_sheet = get_balance_sheet(xbrl_json)
balance_sheet.to_csv("tsla-20250630_BS.csv", index=False)
cash_flows = get_cash_flow_statement(xbrl_json)
cash_flows.to_csv("tsla-20250630_CF.csv", index=False)



from pathlib import Path
import requests

class FinancialStatementsRetriever:
    """
    Retrieve SEC financial statements either from the SEC API
    or from local offline data, depending on `mode`.

    Args:
        ticker (str): Stock ticker (e.g. "TSLA").
        sec_api_key (str): API key for SEC or related service.
        mode (str): One of {"live", "offline"}.
    """

    SEC_EDGAR_URL_PREFIX = "https://www.sec.gov/Archives/edgar/data/"

    def __init__(self, ticker: str, cik: str, sec_api_key: str = SEC_API_KEY, mode: str = "offline"):
        self.ticker = ticker.upper()
        self.cik = cik.upper()
        self.api_key = sec_api_key
        self.mode = mode.lower()

        if self.mode not in {"live", "offline"}:
            raise ValueError(f"Invalid mode: {mode!r}. Must be 'live' or 'offline'.")

        # For offline mode, point to your local folder
        self.offline_dir = OFFLINE_DATA_FOLDER

    def fetch(self, statement: str) -> pd.DataFrame:
        """
        Fetch one type of statement (balance_sheet, income_statement, etc).
        Returns: pandas.DataFrame
        """
        if self.mode == "live":
            return self._fetch_from_sec_api(statement)
        else:
            return self._fetch_from_offline(statement)

    # ---------------- private helpers ---------------- #

    def _fetch_from_sec_api(self, statement: str, datetime: str) -> pd.DataFrame:
        xbrlApi = XbrlApi(SEC_API_KEY)
        # 10-K HTM File URL example
        url_tsla_10_q = '1318605/000162828025035806/tsla-20250630.htm'
        xbrl_json = xbrlApi.xbrl_to_json(htm_url=url_tsla_10_q)

        url = f"https://api.sec.gov/data/{self.ticker}/{statement}.json"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        return pd.DataFrame(data)

    def _fetch_from_offline(self, statement: str, datetime: str, option: str) -> pd.DataFrame:
        file_path = self.offline_dir / f"{self.ticker.lower()}_{datetime}_{statement}{option}.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Offline file not found: {file_path}")
        return pd.read_csv(file_path)
