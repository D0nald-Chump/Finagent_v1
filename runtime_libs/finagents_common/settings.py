from pydantic import BaseModel
from pathlib import Path
import yaml

class DataLoaderSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8081
    arelle_path: str | None = None  # path to Arelle CLI if used
    storage_dir: str = ".cache/sec"

    @staticmethod
    def from_yaml(path: str | Path) -> "DataLoaderSettings":
        data = yaml.safe_load(Path(path).read_text()) or {}
        return DataLoaderSettings(**data)