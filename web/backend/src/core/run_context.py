"""Read and validate frozen runs without reinterpreting live configuration."""
import uuid
from core.errors import DomainError
from core.hashes import digest
from modules.runs.models import Run


def source_data_id(source):
    """A deduplicated import keeps its own request identity, not duplicate observations."""
    return (
        uuid.UUID(source.config_snapshot["resolved_source_import_run_id"])
        if source.config_snapshot.get("resolved_source_import_run_id")
        else source.id
    )


def required_run(session, key, kind=None, complete=False, _ancestors=frozenset()):
    row = session.get(Run, key)
    if row is None:
        raise DomainError("not_found", "Run does not exist", 404)
    if complete and row.status != "complete":
        raise DomainError("run_not_complete", "Results require a complete run", 409)
    if kind and row.kind != kind:
        raise DomainError("parent_mismatch", "Parent has the wrong run kind", 409)
    if complete:
        if row.id in _ancestors:
            raise DomainError("parent_mismatch", "Parent graph contains a cycle", 409)
        if digest(row.config_snapshot) != row.config_sha256:
            raise DomainError(
                "parent_mismatch", "Frozen run configuration checksum differs", 409
            )
        for attr, expected_kind in [
            ("source_import_run_id", "source_import"),
            ("forecast_run_id", "forecast"),
        ]:
            parent_id = getattr(row, attr)
            if not parent_id:
                continue
            parent = required_run(
                session,
                parent_id,
                expected_kind,
                complete=True,
                _ancestors=_ancestors | {row.id},
            )
            if (
                parent is None
                or parent.status != "complete"
                or parent.kind != expected_kind
                or parent.source_sha256 != row.source_sha256
                or parent.target_version != row.target_version
            ):
                raise DomainError(
                    "parent_mismatch", "A frozen parent is no longer compatible", 409
                )
            frozen = row.config_snapshot.get(
                "source_parent_config_sha256"
                if attr == "source_import_run_id"
                else "forecast_parent_config_sha256"
            )
            if frozen and parent.config_sha256 != frozen:
                raise DomainError(
                    "parent_mismatch", "Parent configuration changed", 409
                )
    return row


def snapshot_maps(session, run):
    snap = run.config_snapshot
    if "catalog_snapshot" not in snap and run.source_import_run_id:
        snap = {**session.get(Run, run.source_import_run_id).config_snapshot, **snap}
    warehouses = {w["id"]: w for w in snap.get("warehouse_snapshot", [])}
    routes = {
        (w["destination_country"], w["carrier"]): w["id"] for w in warehouses.values()
    }
    items = {
        i["item_id"]: {
            **i,
            "warehouse_id": routes[(i["destination_country"], i["carrier"])],
        }
        for i in snap.get("catalog_snapshot", [])
    }
    policies = {p["id"]: p for p in snap.get("policies", [])}
    return warehouses, items, policies
