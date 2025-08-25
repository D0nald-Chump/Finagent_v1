from pathlib import Path

# Resolve relative to this file: modules/dataloader/financial_statements
PKG_FOLDER = Path(__file__).parent.resolve()
OFFLINE_DATA_FOLDER = PKG_FOLDER.parent / "offline_data"

__all__ = ["OFFLINE_DATA_FOLDER"]
