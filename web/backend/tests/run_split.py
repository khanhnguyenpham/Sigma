"""0016 moved run JSON into run_configs/run_results and dropped verification checksums.

Migration tests snapshot every table at an older revision and compare after upgrading; they read `runs` through
this view and ignore the dropped checksum keys, so every other stored value must still survive.
"""
NEW_TABLES = {"run_configs", "run_results"}
DROPPED = ("source_sha256", "code_sha256", "config_sha256", "request_sha256", "selection_sha256",
           "parent_bundle_sha256")
RUNS_VIEW = ("(SELECT runs.*, c.config_snapshot, x.result_summary, x.artifact_manifest FROM runs "
             "JOIN run_configs c ON c.run_id=runs.id JOIN run_results x ON x.run_id=runs.id)")


def relation(name, split=True):
    """FROM target for a table; `split=False` reads the pre-0016 runs table directly."""
    return RUNS_VIEW if name == "runs" and split else f'"{name}"'


def without_dropped(jsonb):
    return f"({jsonb} - ARRAY[{','.join(repr(c) for c in DROPPED)}])"


# Pre-0015 rows read the policy table under its old name with the derived supplier_id removed.
LEGACY_ROW = without_dropped("to_jsonb(t)-'supplier_id'")
