"""Split runs into identity/status, frozen configuration and results; drop verification hashes (M5, G5/G6).

Moves runs.config_snapshot to run_configs and runs.result_summary/artifact_manifest to run_results, one row per
run, so every historical run stays readable. Drops the checksum columns runs.source_sha256, code_sha256,
config_sha256, request_sha256, selection_sha256 and route_forecasts.parent_bundle_sha256. request_key stays the
idempotency key; a replayed key is now compared with the frozen request body instead of its hash.

Downgrade restores the columns. config/request/selection checksums are recomputed from the frozen JSON with the
pre-M5 digest; source_sha256 and parent_bundle_sha256 cannot be recovered and stay NULL, and code_sha256 gets a
placeholder, so a queued run must be re-enqueued after a downgrade.
"""
import hashlib
import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0016_run_tables"
down_revision = "0015_item_policies"
branch_labels = None
depends_on = None

HASHES = ("source_sha256", "code_sha256", "config_sha256", "request_sha256", "selection_sha256")


def upgrade():
    op.create_table(
        "run_configs",
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("config_snapshot", JSONB, nullable=False),
    )
    op.create_table(
        "run_results",
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("result_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("artifact_manifest", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.execute("INSERT INTO run_configs (run_id, config_snapshot) SELECT id, config_snapshot FROM runs")
    op.execute("INSERT INTO run_results (run_id, result_summary, artifact_manifest) "
               "SELECT id, result_summary, artifact_manifest FROM runs")
    for column in ("config_snapshot", "result_summary", "artifact_manifest", *HASHES):
        op.drop_column("runs", column)
    op.drop_column("route_forecasts", "parent_bundle_sha256")


def _digest(value):
    # Frozen copy of the pre-M5 core.hashes.digest, so downgrade does not depend on live code.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str,
                                     allow_nan=False).encode()).hexdigest()


def downgrade():
    op.add_column("route_forecasts", sa.Column("parent_bundle_sha256", sa.Text))
    op.add_column("runs", sa.Column("source_sha256", sa.String(64)))
    op.add_column("runs", sa.Column("code_sha256", sa.String(64)))
    op.add_column("runs", sa.Column("config_snapshot", JSONB))
    op.add_column("runs", sa.Column("config_sha256", sa.String(64)))
    op.add_column("runs", sa.Column("request_sha256", sa.String(64)))
    op.add_column("runs", sa.Column("selection_sha256", sa.String(64)))
    op.add_column("runs", sa.Column("result_summary", JSONB))
    op.add_column("runs", sa.Column("artifact_manifest", JSONB))
    op.execute("UPDATE runs r SET config_snapshot=c.config_snapshot FROM run_configs c WHERE c.run_id=r.id")
    op.execute("UPDATE runs r SET result_summary=x.result_summary, artifact_manifest=x.artifact_manifest "
               "FROM run_results x WHERE x.run_id=r.id")
    bind = op.get_bind()
    update = sa.text("UPDATE runs SET code_sha256=:code, config_sha256=:config, request_sha256=:request, "
                     "selection_sha256=:selection WHERE id=:id")
    for key, snapshot in bind.execute(sa.text("SELECT id, config_snapshot FROM runs")).all():
        bind.execute(update, dict(
            id=key, code="0" * 64, config=_digest(snapshot), request=_digest(snapshot.get("request", {})),
            selection=_digest(snapshot["selections"]) if "selections" in snapshot else None))
    for column in ("code_sha256", "config_snapshot", "config_sha256", "request_sha256", "result_summary",
                   "artifact_manifest"):
        op.alter_column("runs", column, nullable=False)
    op.drop_table("run_results")
    op.drop_table("run_configs")
