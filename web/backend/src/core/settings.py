"""Local configuration; HTTP never resolves arbitrary filesystem paths."""

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PROFILE = {
    "version": "m3-design-v1",
    "lead_time_days": 7,
    "review_days": 1,
    "horizon_days": 14,
}


@dataclass(frozen=True)
class Settings:
    database_url: str
    source_root: Path
    output_root: Path
    frontend_origin: str = "http://127.0.0.1:5173"
    mode: str = "local"
    worker_instance: str = ""
    demo_root: Path | None = None

    @classmethod
    def from_env(cls):
        project = PROJECT_ROOT
        mode = os.environ.get("M3_MODE", "local")
        if mode not in {"local", "demo"}:
            raise ValueError("M3_MODE must be local or demo")
        url = os.environ.get("M3_DATABASE_URL", "")
        if mode == "demo":
            try:
                parsed = make_url(url)
                if parsed.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
                    raise ValueError()
                if parsed.database not in {"sigma_demo", "sigma_m3_test"}:
                    raise ValueError()
                url = parsed.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
            except Exception:
                raise ValueError("Demo requires PostgreSQL database sigma_demo (or sigma_m3_test for checks)") from None
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("M3_DATABASE_URL must use PostgreSQL with psycopg")
        origin = os.environ.get("M3_FRONTEND_ORIGIN", "http://127.0.0.1:5173")
        try:
            endpoint = urlsplit(origin)
            valid_https = (endpoint.scheme == "https" and endpoint.hostname and endpoint.port != 0
                and not endpoint.username and not endpoint.password and not endpoint.path
                and not endpoint.query and not endpoint.fragment and "*" not in origin
                and not any(c.isspace() for c in origin))
        except ValueError:
            valid_https = False
        if origin not in {"http://127.0.0.1:5173", "http://localhost:5173"} and not (mode == "demo" and valid_https):
            raise ValueError("M3 v1 accepts a local frontend only")
        if mode == "demo" and not all(os.environ.get(k) for k in ("M3_DEMO_ROOT", "M3_SOURCE_ROOT", "M3_OUTPUT_ROOT")):
            raise ValueError("Demo requires explicit demo, source and output roots")
        source = Path(os.environ.get("M3_SOURCE_ROOT", project)).resolve()
        output = Path(os.environ.get("M3_OUTPUT_ROOT", project / "outputs/m3")).resolve()
        demo_root = Path(os.environ["M3_DEMO_ROOT"]).resolve() if mode == "demo" else None
        if mode == "demo" and (demo_root.name != "sigma-demo" or demo_root == project
                or demo_root in project.parents or not source.is_relative_to(demo_root)
                or not output.is_relative_to(demo_root) or source == output
                or source in output.parents or output in source.parents):
            raise ValueError("Demo needs separate source/output directories under an isolated sigma-demo root")
        return cls(
            url,
            source,
            output,
            origin,
            mode,
            os.environ.get("M3_WORKER_INSTANCE", ""),
            demo_root,
        )

    def order_source(self, key):
        if key != "orders_snapshot":
            raise ValueError("Unknown source key")
        return self.source_root / "data/sigma_sim_data_orders.csv"
