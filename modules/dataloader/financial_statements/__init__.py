from pathlib import Path

# Resolve relative to this file: modules/dataloader/financial_statements
PKG_FOLDER = Path(__file__).parent.parent.resolve()
OFFLINE_DATA_FOLDER = PKG_FOLDER / "offline_data"

config = {}
with open(PKG_FOLDER / ".dataloader_config") as f:
    for line in f:
        if "=" in line:
            key, val = line.strip().split("=", 1)
            config[key] = val

SEC_API_KEY = config["sec_api_key"]

__all__ = ["OFFLINE_DATA_FOLDER", "SEC_API_KEY"]
