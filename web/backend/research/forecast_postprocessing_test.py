"""F4 only: test the already locked validation representative against C00."""

import argparse
import csv
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import traceback
import uuid

from core.hashes import code_digest
from web.backend.research import forecast_postprocessing_validation as validation
from web.backend.research import forecast_postprocessing_test_verification as verification


ROOT = Path(__file__).resolve().parents[3]


def outcome(summaries, representative, parameters):
    validation.identity.require([r["candidate_id"] for r in summaries] == ["C00", representative]
                                and representative != "C00", "Only baseline and locked representative are allowed")
    target = validation.post.load_protocol()["evaluation"]["test_target"]
    validation.identity.require(all(r["valid"] is True and r["metrics"]["event_denominator"] == target["event_denominator"]
                                    for r in summaries), "Test cohort or coverage differs")
    return dict(representative_id=representative, selected_on="validation", parameters_sha256=parameters["sha256"],
                target=target, target_met=summaries[1]["metrics"]["early_numerator"] >= target["early_numerator"],
                retrospective=True, reselection=False, source_F3_manifest_sha256=verification.F3_MANIFEST_SHA256)


def run(f3_run, output_root):
    source, baseline, cases, parameters, _, representative = verification.load_locked_test(f3_run)
    validation.identity.coverage(source, baseline)
    p = validation.post.load_protocol()
    output_root = Path(output_root).resolve()
    validation.identity.require(output_root.is_relative_to(ROOT / "outputs/research")
                                and not output_root.is_relative_to(Path(f3_run).resolve()), "Unsafe private output path")
    folder = output_root / ("forecast-test-v1-" + str(uuid.uuid4()))
    folder.mkdir(parents=True, exist_ok=False)
    code = {Path(f).resolve().relative_to(ROOT).as_posix(): validation.audit.sha(f) for f in [__file__, verification.__file__]}
    validation.audit.write(folder / "execution_lock.json", dict(created_at=datetime.now(timezone.utc).isoformat(),
        phase="F4_test_only", representative_id=representative, source_F3_manifest_sha256=verification.F3_MANIFEST_SHA256,
        source_F3_receipt_sha256=verification.F3_RECEIPT_SHA256, code_sha256=code, parameter_updates=False, reselection=False))
    (folder / "parameters.json").write_bytes((Path(f3_run) / "parameters.json").read_bytes())
    summaries, rows = [], []
    for candidate in ("C00", representative):
        spec = next(s for s in p["candidates"] if s["id"] == candidate)
        summary = validation.calculate_candidate(spec, source, baseline, cases, parameters, folder / candidate)
        summaries.append(summary)
        rows.append(validation.table_row(summary, validation.audit.read(folder / candidate / "forecast_metrics.json.gz")))
        print("Calculated test " + candidate, flush=True)
    evaluation = outcome(summaries, representative, parameters)
    validation.audit.write(folder / "summary.json", summaries)
    validation.audit.write(folder / "evaluation.json", evaluation)
    with (folder / "summary.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(validation.HEADERS)
        writer.writerows(rows)
    cells = "".join("<tr>" + "".join("<td>" + html.escape(value) + "</td>" for value in row) + "</tr>" for row in rows)
    (folder / "report.html").write_text("<!doctype html><meta charset='utf-8'><title>SIGMA F4 retrospective test</title>"
        "<h1>F4 test — independent verification required</h1><p>Only C00 and the validation-locked representative. "
        "Original parameters and fixed inventory/orders/events; no refit/reselection/default change. Test has been seen historically. "
        "Target: at least 261/578. No accepted false-alarm budget or R07/T14 acceptance.</p><table border='1'><tr>" +
        "".join("<th>" + h + "</th>" for h in validation.HEADERS) + "</tr>" + cells + "</table><p>See evaluation.json and "
        "verification.json; point forecast error and alarm tradeoffs remain separate. Full metrics and common-pair date errors "
        "are retained in each candidate folder.</p>", encoding="utf-8")
    validation.audit.write(folder / "manifest.json", dict(status="calculated_unverified", phase="F4_test_only", protocol=p,
        protocol_sha256=validation.post.PROTOCOL_SHA256, application_code_sha256=code_digest(), source_F3_run=str(Path(f3_run).resolve()),
        source_F3_manifest_sha256=verification.F3_MANIFEST_SHA256, source_F3_receipt_sha256=verification.F3_RECEIPT_SHA256,
        code_sha256=code, reselection=False, artifacts={f.relative_to(folder).as_posix(): validation.audit.sha(f)
                                                     for f in folder.rglob("*") if f.is_file()}))
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    native = commands.add_parser("test")
    native.add_argument("--f3-run", type=Path, required=True)
    native.add_argument("--output-root", type=Path, default=ROOT / "outputs/research/forecast-postprocessing-f4")
    check = commands.add_parser("verify")
    check.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "test":
            folder = run(args.f3_run, args.output_root)
            print(json.dumps(dict(status="calculated_unverified", output=str(folder))))
        else:
            print(json.dumps(verification.verify(args.run_dir)))
        return 0
    except Exception as exc:
        cp = ROOT / "outputs/research/forecast-postprocessing-f4-checkpoint"
        cp.mkdir(parents=True, exist_ok=True)
        (cp / ("failure-" + str(uuid.uuid4()) + ".private.log")).write_text(traceback.format_exc(), encoding="utf-8")
        print(json.dumps(dict(status="failed", error_type=type(exc).__name__)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
