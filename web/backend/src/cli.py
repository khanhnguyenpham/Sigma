"""CLI and API share the same validation, idempotency and run services."""

import argparse, json, uuid
from datetime import date
from core.db import database
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from core.run_context import required_run
from core.settings import Settings
from worker import serve


def main():
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import-orders")
    imp.add_argument(
        "--source-key", default="orders_snapshot", choices=["orders_snapshot"]
    )
    imp.add_argument("--as-of-date", default="2025-12-31")
    imp.add_argument("--request-key")
    imp.add_argument("--wait", action="store_true")
    status = commands.add_parser("status")
    status.add_argument("--run-id", type=uuid.UUID, required=True)
    seed = commands.add_parser("seed-simulation")
    seed.add_argument("--source-run", type=uuid.UUID, required=True)
    seed.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    forecast = commands.add_parser("forecast")
    forecast.add_argument("--source-run", type=uuid.UUID, required=True)
    forecast.add_argument("--as-of-date", default="2025-12-31")
    forecast.add_argument("--mode", choices=["replay", "future"], default="replay")
    forecast.add_argument("--forecast-run", type=uuid.UUID)
    forecast.add_argument("--request-key")
    forecast.add_argument("--wait", action="store_true")
    sim = commands.add_parser("simulate")
    sim.add_argument(
        "--kind",
        choices=["policy_replay", "alert_replay", "stock_projection"],
        required=True,
    )
    sim.add_argument("--source-run", type=uuid.UUID)
    sim.add_argument("--forecast-run", type=uuid.UUID, required=True)
    sim.add_argument("--scenario-id", type=int, required=True)
    sim.add_argument("--as-of-date", required=True)
    sim.add_argument("--period-start")
    sim.add_argument("--period-end")
    sim.add_argument("--request-key")
    sim.add_argument("--wait", action="store_true")
    verify = commands.add_parser("verify")
    verify.add_argument("--run-id", type=uuid.UUID, required=True)
    monthly = commands.add_parser("prepare-monthly")
    monthly.add_argument("--source-run", type=uuid.UUID, required=True)
    monthly.add_argument("--verification-receipt", required=True)
    args = p.parse_args()
    settings = Settings.from_env()
    engine, sessions = database(settings.database_url)
    try:
        if args.command == "prepare-monthly":
            from modules.reporting.monthly import prepare

            with sessions() as session:
                result = prepare(
                    settings, session, args.source_run, args.verification_receipt
                )
            print(json.dumps(result, default=str, allow_nan=False))
            return
        if args.command == "seed-simulation":
            from modules.inventory.seeding import seed_simulation

            with sessions.begin() as session:
                result = seed_simulation(session, args.source_run, args.as_of_date)
            print(json.dumps(result))
            return
        if args.command == "verify":
            from modules.runs.verification import verify_run

            print(json.dumps(verify_run(settings, sessions, args.run_id), default=str))
            return
        if args.command in {"import-orders", "forecast", "simulate"}:
            if args.command == "simulate" and args.source_run is None:
                with sessions() as s:
                    args.source_run = required_run(
                        s, args.forecast_run, "forecast", complete=True
                    ).source_import_run_id
            request = (
                RunCreate(
                    kind="source_import",
                    as_of_date=args.as_of_date,
                    source_key=args.source_key,
                )
                if args.command == "import-orders"
                else RunCreate(
                    kind="forecast",
                    source_import_run_id=args.source_run,
                    as_of_date=args.as_of_date,
                    mode=args.mode,
                    forecast_run_id=args.forecast_run,
                )
                if args.command == "forecast"
                else RunCreate(
                    kind=args.kind,
                    source_import_run_id=args.source_run,
                    forecast_run_id=args.forecast_run,
                    scenario_id=args.scenario_id,
                    as_of_date=args.as_of_date,
                    period_start=args.period_start,
                    period_end=args.period_end,
                )
            )
            with sessions.begin() as session:
                row, _ = enqueue(
                    session, request, args.request_key or str(uuid.uuid4())
                )
                key = row.id
            if args.wait:
                # Run the ordinary locked worker. Existing earlier queue entries are processed first.
                while True:
                    with sessions() as session:
                        state = required_run(session, key).status
                    if state in {"complete", "failed", "invalidated"}:
                        break
                    serve(settings, once=True)
                if state != "complete":
                    raise SystemExit("Run did not complete; inspect status/error_code")
        else:
            key = args.run_id
        with sessions() as session:
            row = required_run(session, key)
            print(
                json.dumps(
                    {
                        "run_id": str(row.id),
                        "kind": row.kind,
                        "status": row.status,
                        "error_code": row.error_code,
                        "summary": row.result_summary,
                    },
                    default=str,
                )
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
