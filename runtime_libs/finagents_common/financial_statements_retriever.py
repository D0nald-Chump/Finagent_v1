import pandas as pd

from modules.dataloader.financial_statements import OFFLINE_DATA_FOLDER


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

    def __init__(self, ticker: str, cik: str, sec_api_key: str, mode: str = "offline"):
        self.ticker = ticker.upper()
        self.cik = cik.upper()
        self.api_key = sec_api_key
        self.mode = mode.lower()

        if self.mode not in {"live", "offline"}:
            raise ValueError(f"Invalid mode: {mode!r}. Must be 'live' or 'offline'.")

        # For offline mode, point to your local folder
        self.offline_dir = OFFLINE_DATA_FOLDER

    def fetch(self, date: str, statement: str) -> pd.DataFrame:
        """
        Fetch one type of statement (balance_sheet, income_statement, etc).
        Returns: pandas.DataFrame
        """
        if self.mode == "live":
            return self._fetch_from_sec_api(date, statement)
        else:
            return self._fetch_from_offline(date, statement)

    # ---------------- private helpers ---------------- #

    def _fetch_from_sec_api(self, statement: str, date: str) -> pd.DataFrame:
        # xbrlApi = XbrlApi(self.api_key)
        # # 10-K HTM File URL example
        # url_tsla_10_q = '1318605/000162828025035806/tsla-20250630.htm'
        # xbrl_json = xbrlApi.xbrl_to_json(htm_url=url_tsla_10_q)
        #
        # url = f"https://api.sec.gov/data/{self.ticker}/{statement}.json"
        # headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        # r = requests.get(url, headers=headers, timeout=30)
        # r.raise_for_status()
        # data = r.json()
        return pd.DataFrame()

    def _fetch_from_offline(self, date: str, statement: str, option: str = "") -> pd.DataFrame:
        file_path = self.offline_dir / f"{self.ticker.lower()}/sec_api/{self.ticker.lower()}_{date}_{statement}{option}.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Offline file not found: {file_path}")
        return pd.read_csv(file_path)

