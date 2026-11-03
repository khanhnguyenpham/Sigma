"""Bind an anonymized demo source to the registered quantity/transaction inputs."""
import json
from pathlib import Path

from core.demo import source_ready
from core.errors import DomainError
from core.hashes import digest
from core.settings import PROJECT_ROOT
from src.common import ITEM


def signatures(sales):
    daily = sales.groupby(["date", *ITEM], sort=True).agg(
        quantity=("quantity", "sum"), orders=("order_id", "nunique")).reset_index()
    quantities = [[str(r.date.date()), r.destination_country, r.carrier, r.sku,
        r.product_type, int(r.quantity), int(r.orders)] for r in daily.itertuples()]
    ordered = sales.sort_values(["order_datetime", "order_id"], kind="mergesort")
    transactions = [[str(r.date.date()), r.destination_country, r.carrier, r.sku,
        r.product_type, int(r.quantity)] for r in ordered.itertuples()]
    return dict(quantity_signature=digest(quantities), transaction_signature=digest(transactions))


def require_registered_source(settings, sales, source_sha, expected=None):
    expected = expected or json.loads((PROJECT_ROOT / "data/configs/m2-final.json").read_text())["source_sha256"]
    if settings.mode == "local" and source_sha == expected:
        return None
    if settings.mode != "demo" or not source_ready(settings):
        raise DomainError("parent_mismatch", "Source must match the registered fixed M2 protocol")
    manifest = json.loads((settings.source_root / "demo-manifest.json").read_text())
    if (manifest.get("source_sha256") != source_sha or manifest.get("parent_source_sha256") != expected
            or any(manifest.get(k) != value for k, value in signatures(sales).items())):
        raise DomainError("parent_mismatch", "Demo source does not preserve registered quantity inputs")
    return {k: manifest[k] for k in ("source_sha256", "parent_source_sha256", "quantity_signature", "transaction_signature")}
