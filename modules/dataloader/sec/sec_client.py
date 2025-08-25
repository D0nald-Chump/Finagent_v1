from __future__ import annotations

import os
import time
from datetime import date
from typing import Dict, List, Tuple

import requests

from sec.constants import SEC_BASE, SEC_DATA_BASE

DEFAULT_HEADERS = {
    "User-Agent": "FinAgents/1.0 (contact: zhangxwsavvy@gmail.com)",
    "Accept-Encoding": "gzip, deflate",
}

class SecClient:
    def __init__(self, user_agent: str | None = None, throttle_seconds: float = 0.2):
        self.headers = dict(DEFAULT_HEADERS)
        if user_agent:
            self.headers["User-Agent"] = user_agent
        self.throttle = throttle_seconds

    @staticmethod
    def _pad_cik(cik: int | str) -> str:
        return str(cik).strip().zfill(10)

    @staticmethod
    def _parse_ymd(s: str) -> date:
        # expects "YYYY-MM-DD"
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))

    def resolve_cik_from_ticker(self, ticker: str) -> str:
        url = f"{SEC_BASE}/files/company_tickers.json"
        r = requests.get(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        t = ticker.upper()
        for _, rec in data.items():
            if rec.get("ticker", "").upper() == t:
                return self._pad_cik(rec["cik_str"])
        raise RuntimeError(f"Could not resolve CIK for ticker {ticker!r}")

    def all_fillings_recent(self, cik_padded: str):
        subs_url = f"{SEC_DATA_BASE}/submissions/CIK{cik_padded}.json"
        r = requests.get(subs_url, headers=self.headers, timeout=30)
        r.raise_for_status()
        subs = r.json()
        return subs.get("filings", {}).get("recent", {})

    def latest_10q_accession(self, cik_padded: str) -> Tuple[str, str]:
        recent = self.all_fillings_recent(cik_padded)
        forms = recent.get("form", [])
        acc_no = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        for i in range(len(forms)):
            if forms[i] == "10-Q":
                return acc_no[i].replace("-", ""), primary_docs[i]
        raise RuntimeError(f"No recent 10-Q for CIK {cik_padded}")

    def all_10q_accession(
            self,
            cik_padded: str,
            start_date: str,
            end_date: str
    ) -> Dict[str, Tuple[str, str]]:
        """
        Return {reportDate: (accession_no_dashes, primary_document_filename)}
        for all 10-Q filings in the inclusive [start_date, end_date] range.

        Dates are ISO "YYYY-MM-DD".
        """
        recent = self.all_fillings_recent(cik_padded)
        forms = recent.get("form", [])
        acc_no = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        report_dates: List[str] = recent.get("reportDate", []) or []

        start = self._parse_ymd(start_date)
        end = self._parse_ymd(end_date)
        date2accessions: Dict[str, Tuple[str, str]] = {}

        # Align lengths defensively
        n = min(len(forms), len(acc_no), len(primary_docs), len(report_dates))
        for i in range(n):
            if forms[i] != "10-Q":
                continue
            rdate_str = report_dates[i]
            try:
                rdate = self._parse_ymd(rdate_str)
            except Exception:
                # Skip malformed dates instead of crashing
                continue
            if start <= rdate <= end:
                date2accessions[rdate_str] = acc_no[i].replace("-", ""), primary_docs[i]
            if rdate <= start:
                # early termination if the current 10-Q's rdate is already prior the specified start date
                return date2accessions
        raise RuntimeError(f"No 10-Qs found for CIK {cik_padded} between {start_date!r} and {end_date!r}")

    def list_filing_files(self, cik_padded: str, accession_nodash: str) -> List[Dict]:
        url = f"{SEC_BASE}/Archives/edgar/data/{int(cik_padded)}/{accession_nodash}/index.json"
        r = requests.get(url, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json().get("directory", {}).get("item", [])

    @staticmethod
    def pick_xbrl_artifacts(items: List[Dict]) -> Dict[str, str | None]:
        names = [it["name"] for it in items]
        instance = None
        for n in names:
            if n.endswith(("_htm.xml", "_ixbrl.xml", ".xml")) and ("htm" in n or "ixbrl" in n):
                instance = n
                break
        if not instance:
            cand = [n for n in names if n.endswith(".xml") and not any(s in n for s in ["_pre", "_cal", "_def", "_lab"])]
            instance = cand[0] if cand else None

        def find_one(suffix: str):
            for n in names:
                if n.endswith(suffix):
                    return n
            return None

        return {
            "instance": instance,
            "pre": find_one("_pre.xml"),
            "def": find_one("_def.xml"),
            "lab": find_one("_lab.xml"),
            "cal": find_one("_cal.xml"),
        }

    def download(
            self,
            cik_padded: str,
            accession_nodash: str,
            artifacts: Dict[str, str | None],
            outdir: str
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        os.makedirs(outdir, exist_ok=True)
        base = f"{SEC_BASE}/Archives/edgar/data/{int(cik_padded)}/{accession_nodash}"
        paths: Dict[str, str] = {}
        url_paths: Dict[str, str] = {}
        for k, fname in artifacts.items():
            if not fname:
                continue
            url = f"{base}/{fname}"
            dest = os.path.join(outdir, fname)
            with requests.get(url, headers=self.headers, timeout=60, stream=True) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            paths[k] = dest
            url_paths[k] = url
            time.sleep(self.throttle)
        return paths, url_paths
