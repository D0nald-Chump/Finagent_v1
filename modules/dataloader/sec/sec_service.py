from datetime import date
from typing import List, Tuple, Dict

from sec.sec_client import SecClient

SEC_CLIENT = SecClient()

def download_10q_between(
        ticker: str,
        start_date: str,
        end_date: str = date.today().isoformat(),
        cik: str | None = None,
        out_dir: str | None = None
) -> List[Tuple[str, str]]:
    """
    High-level entry point used by FinAgents.

    - Resolves CIK if not provided, finds latest 10-Q, downloads XBRL artifacts
    - Loads with Arelle and reconstructs BS/IS/CF/SE using presentation roles
    - Returns dict of DataFrames; optionally persists CSVs if out_dir provided
    """
    cik = SEC_CLIENT.resolve_cik_from_ticker(ticker) if cik is None else cik
    date2accessions = SEC_CLIENT.all_10q_accession(cik, start_date, end_date)

    paths_urls_10q = []

    for accession, instance in date2accessions.values():
        paths, url_paths = SEC_CLIENT.download(cik, accession, {"instance": instance}, out_dir)
        paths_urls_10q.append((paths["instance"], url_paths["instance"]))

    return paths_urls_10q


def download_latest_10q(
        ticker: str,
        out_dir: str,
        cik: str | None = None,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    High-level entry point used by FinAgents.

    - Resolves CIK if not provided, finds latest 10-Q, downloads XBRL artifacts
    - Loads with Arelle and reconstructs BS/IS/CF/SE using presentation roles
    - Returns dict of DataFrames; optionally persists CSVs if out_dir provided
    """
    cik = SEC_CLIENT.resolve_cik_from_ticker(ticker) if cik is None else cik
    accession, _ = SEC_CLIENT.latest_10q_accession(cik)
    items = SEC_CLIENT.list_filing_files(cik, accession)
    artifacts = SEC_CLIENT.pick_xbrl_artifacts(items)

    return SEC_CLIENT.download(cik, accession, artifacts, out_dir)
