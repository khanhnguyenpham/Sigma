"""Local configuration; HTTP never resolves arbitrary filesystem paths."""

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class Settings:
    database_url: str
    source_root: Path
    output_root: Path
    frontend_origin: str = "http://127.0.0.1:5173"

    @classmethod
    def from_env(cls):
        project = PROJECT_ROOT
        url = os.environ.get("M3_DATABASE_URL", "")
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("M3_DATABASE_URL must use PostgreSQL with psycopg")
        origin = os.environ.get("M3_FRONTEND_ORIGIN", "http://127.0.0.1:5173")
        if origin not in {"http://127.0.0.1:5173", "http://localhost:5173"}:
            raise ValueError("M3 v1 accepts a local frontend only")
        return cls(
            url,
            Path(os.environ.get("M3_SOURCE_ROOT", project)).resolve(),
            Path(os.environ.get("M3_OUTPUT_ROOT", project / "outputs/m3")).resolve(),
            origin,
        )

    def order_source(self, key):
        if key != "orders_snapshot":
            raise ValueError("Unknown source key")
        return self.source_root / "data/sigma_sim_data_orders.csv"
