"""SIGMA local CLI. Real inputs and run artifacts never leave this machine."""
from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

from src.common import ROOT, ROUTE, DataQualityError, code_hash, new_manifest, read_config, seal_manifest, sha256, write_csv, write_json
from src.data import audit_orders, daily_sales, observed_anomalies, route_top
from src.evaluation import acceptance, metric_table, select_models
from src.inventory import initialize_partners, item_matrix, replay_alerts, run_policy, simulation_metrics, alert_opportunity_summary, AllocationPlan
from src.models import baseline_backtest, forecast_at, lgbm_rolling, sarima_validation, selected_backtest, robust_validation, distribution_validation
from src.context_models import context_validation
from src.validation_cache import import_validation
from src.count_models import COUNT_SPECS, MONTHLY_COUNT_SPECS, count_rolling
from src.reporting import eda, generate_synthetic
from src.calendar_models import calendar_validation
from src.transactions import EVENT_COLUMNS, prepare_transactions
from src.cohort_models import COHORT_SPECS, cohort_rolling
from src.hierarchical_models import HIERARCHICAL_SPECS, hierarchical_rolling
from src.monthly_lad import MONTHLY_LAD_SPECS

STAGES = ["audit", "eda", "baseline", "validation", "test", "forecast", "inventory"]


def progress(message):
    print(message, flush=True)


def read_predictions(path):
    return pd.read_csv(path, parse_dates=["as_of_date", "target_date", "forecast_date"])


def execute(config="config.json", stage="all", run_id=None, demo=False, baseline_only=False, resume=False, validation_cache_run=None):
    cfg = read_config(config)
    run_id = run_id or ("demo_" if demo else "sigma_") + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("Invalid run id")
    root = (ROOT / cfg["output_root"]).resolve()
    if not root.is_relative_to(ROOT):
        raise ValueError("Output root must stay within the project")
    folder = root / run_id
    if validation_cache_run and (demo or baseline_only):
        raise ValueError('Historical validation import is only for a full private run')
    if validation_cache_run and not re.fullmatch(r'[A-Za-z0-9_-]+',validation_cache_run):
        raise ValueError('Invalid historical validation run id')
    if folder.exists() and any(folder.iterdir()) and not resume:
        raise ValueError("Run exists; use a new id or explicitly --resume")
    if resume and not (folder / 'manifest.json').is_file():
        raise ValueError('Cannot resume without the original manifest; use a new run id')
    folder.mkdir(parents=True, exist_ok=True)
    source = (ROOT / cfg["source"]).resolve()
    if demo:
        source = folder / 'synthetic_orders.csv'
        if resume:
            if not source.is_file():
                raise ValueError('Original synthetic source is missing; choose a new run id')
        else:
            generate_synthetic(source, cfg)
    if not source.is_relative_to(ROOT):
        raise ValueError("Source must be local to the project")
    sales, audit = audit_orders(source, cfg)
    cfg = initialize_partners(sales, cfg)
    if resume and (folder / "manifest.json").exists():
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["source_sha256"] != sha256(source) or manifest["config"] != cfg or manifest["code_sha256"] != code_hash():
            raise ValueError("Resume requires the same input, configuration and code; use a new run")
        if manifest["execution_mode"] != ("baseline_demo" if baseline_only else "full"):
            raise ValueError("Cannot change model mode while resuming")
    else:
        manifest = new_manifest(cfg, source, run_id)
        manifest['source_relative_path'] = source.relative_to(ROOT).as_posix()
        manifest["source_kind"] = "generated_synthetic" if demo else "private_order_snapshot"
        manifest["execution_mode"] = "baseline_demo" if baseline_only else "full"
    manifest["evaluation_protocol"] = cfg.get("evaluation_protocol", "first_locked_test")
    manifest["status"] = "running"
    write_json(folder / "manifest.json", manifest)
    daily = daily_sales(sales, cfg)
    top = route_top(daily, cfg)
    requested = STAGES if stage == "all" else [stage]
    try:
        for current in requested:
            if resume and manifest["stages"].get(current) == "complete":
                from src.common import validate_run
                validate_run(folder, require_complete=False)
                progress(f"Stage already complete: {current}")
                continue
            progress(f"Stage: {current}")
            if current == "audit":
                write_json(folder / "data_audit.json", audit)
                write_json(folder / "effective_config.json", cfg)
                write_csv(folder / "daily_sales.csv", daily)
                write_csv(folder / "top_routes.csv", top)
                write_csv(folder / "observed_anomalies.csv", observed_anomalies(daily, cfg))
            elif current == "eda":
                eda(daily, folder, cfg)
            elif current == "baseline":
                predictions, logs = baseline_backtest(daily, cfg)
                write_csv(folder / "baseline_validation_predictions.csv", predictions)
                write_csv(folder / "baseline_metrics.csv", metric_table(predictions[predictions.split.eq("validation")]))
                write_csv(folder / "baseline_log.csv", logs)
            elif current == "validation":
                baseline_predictions = read_predictions(folder / "baseline_validation_predictions.csv")
                frames = [baseline_predictions]
                imported_families = []
                failed = set()
                decision = {"condition": "Any train top10 above 20% validation h1-7 after SARIMA", "triggered": False}
                if not baseline_only and not validation_cache_run:
                    sarima, sarima_logs = sarima_validation(daily, top, cfg, progress)
                    write_csv(folder / "sarima_validation_predictions.csv", sarima)
                    write_csv(folder / "sarima_log.csv", sarima_logs)
                    failures = sarima_logs.loc[sarima_logs.status.eq("failed")]
                    failed = {((r.destination_country, r.carrier), r.model) for r in failures.itertuples(index=False)}
                    frames.append(sarima)
                validation = pd.concat(frames, ignore_index=True)
                metrics = metric_table(validation[validation.split.eq("validation")])
                if validation_cache_run:
                    metrics, failed, evidence = import_validation(root / validation_cache_run,
                        folder, cfg, manifest['source_sha256'], daily, top)
                    manifest['validation_import'] = evidence
                    imported_families = evidence['imported_model_families']
                provisional = select_models(metrics, top, cfg, failed)
                trigger = provisional.loc[provisional.is_top10, "validation_target_met"].eq(False).any()
                if trigger and not baseline_only and not validation_cache_run:
                    ids = [f"lgbm_{leaves}_{minimum}" for leaves in [15, 31] for minimum in [20, 50]]
                    lgbm, logs = lgbm_rolling(daily, top, cfg, ids, "validation", progress)
                    write_csv(folder / "lightgbm_validation_predictions.csv", lgbm)
                    write_csv(folder / "lightgbm_log.csv", logs)
                    validation = pd.concat([validation, lgbm], ignore_index=True)
                    metrics = metric_table(validation[validation.split.eq("validation")])
                    decision["triggered"] = True
                if cfg.get("tuning", {}).get("enabled") and not baseline_only and not validation_cache_run:
                    robust, robust_logs = robust_validation(daily, top, cfg)
                    ids = [f"lgbm_mape_{leaves}_{minimum}" for leaves in [15, 31] for minimum in [20, 50]]
                    tuned, tuned_logs = lgbm_rolling(daily, top, cfg, ids, "validation", progress)
                    write_csv(folder / "tuning_validation_predictions.csv", pd.concat([robust, tuned], ignore_index=True))
                    write_csv(folder / "tuning_log.csv", pd.concat([robust_logs, tuned_logs], ignore_index=True))
                    validation = pd.concat([validation, robust, tuned], ignore_index=True)
                    metrics = metric_table(validation[validation.split.eq("validation")])
                    if cfg["tuning"].get("calendar_enabled"):
                        calendar, calendar_logs = calendar_validation(daily, top, cfg, progress)
                        write_csv(folder / "calendar_validation_predictions.csv", calendar)
                        write_csv(folder / "calendar_log.csv", calendar_logs)
                        validation = pd.concat([validation, calendar], ignore_index=True)
                        metrics = metric_table(validation[validation.split.eq("validation")])
                    write_json(folder / "tuning_protocol.json", cfg["tuning"])
                if cfg.get('tuning',{}).get('context_enabled') and not baseline_only and 'context' not in imported_families:
                    context, context_logs = context_validation(daily, top, cfg, progress)
                    write_csv(folder / 'context_validation_predictions.csv', context)
                    write_csv(folder / 'context_log.csv', context_logs)
                    metrics = pd.concat([metrics, metric_table(context.loc[context.split.eq('validation')])], ignore_index=True)
                if cfg.get('tuning',{}).get('distribution_enabled') and not baseline_only and 'distribution' not in imported_families:
                    distribution, distribution_logs = distribution_validation(daily, top, cfg)
                    write_csv(folder / 'distribution_validation_predictions.csv', distribution)
                    write_csv(folder / 'distribution_log.csv', distribution_logs)
                    metrics = pd.concat([metrics, metric_table(distribution.loc[distribution.split.eq('validation')])], ignore_index=True)
                if cfg.get('tuning',{}).get('count_enabled') and not baseline_only and 'count' not in imported_families:
                    count, count_logs = count_rolling(daily,sales,top,cfg,list(COUNT_SPECS),'validation',progress)
                    write_csv(folder / 'count_validation_predictions.csv',count)
                    write_csv(folder / 'count_log.csv',count_logs)
                    metrics = pd.concat([metrics,metric_table(count.loc[count.split.eq('validation')])],ignore_index=True)
                if cfg.get('tuning',{}).get('cohort_enabled') and not baseline_only and 'cohort' not in imported_families:
                    cohort, cohort_logs = cohort_rolling(daily,sales,top,cfg,[name for name,_,_ in COHORT_SPECS],'validation',progress)
                    write_csv(folder / 'cohort_validation_predictions.csv',cohort)
                    write_csv(folder / 'cohort_log.csv',cohort_logs)
                    metrics = pd.concat([metrics,metric_table(cohort.loc[cohort.split.eq('validation')])],ignore_index=True)
                if cfg.get('tuning',{}).get('countmonth_enabled') and not baseline_only and 'countmonth' not in imported_families:
                    monthly, monthly_logs = count_rolling(daily,sales,top,cfg,list(MONTHLY_COUNT_SPECS),'validation',progress)
                    write_csv(folder / 'countmonth_validation_predictions.csv',monthly)
                    write_csv(folder / 'countmonth_log.csv',monthly_logs)
                    metrics = pd.concat([metrics,metric_table(monthly.loc[monthly.split.eq('validation')])],ignore_index=True)
                if cfg.get('tuning',{}).get('hiercount_enabled') and not baseline_only and 'hiercount' not in imported_families:
                    hierarchy, hierarchy_logs = hierarchical_rolling(daily,sales,top,cfg,list(HIERARCHICAL_SPECS),'validation',progress)
                    write_csv(folder / 'hiercount_validation_predictions.csv',hierarchy)
                    write_csv(folder / 'hiercount_log.csv',hierarchy_logs)
                    metrics = pd.concat([metrics,metric_table(hierarchy.loc[hierarchy.split.eq('validation')])],ignore_index=True)
                if cfg.get('tuning',{}).get('monthlad_enabled') and not baseline_only and 'monthlad' not in imported_families:
                    monthly_frames,monthly_logs=[],[]
                    from src.models import series_by_route,rolling_route
                    monthly_series=series_by_route(daily)
                    for keys in map(tuple,top[ROUTE].to_numpy()):
                        for model_id in MONTHLY_LAD_SPECS:
                            frame,log=rolling_route(monthly_series[keys],keys,model_id,cfg['validation_start'],cfg['validation_end'],cfg)
                            frame['split']=np.where(frame.target_date.le(pd.Timestamp(cfg['validation_end'])),'validation','outside_validation')
                            monthly_frames.append(frame);monthly_logs.append(log)
                    monthly=pd.concat(monthly_frames,ignore_index=True)
                    write_csv(folder/'monthlad_validation_predictions.csv',monthly)
                    write_csv(folder/'monthlad_log.csv',pd.concat(monthly_logs,ignore_index=True))
                    metrics=pd.concat([metrics,metric_table(monthly.loc[monthly.split.eq('validation')])],ignore_index=True)
                write_json(folder / 'tuning_protocol.json', cfg.get('tuning',{}))
                decision["reason"] = "Baseline demonstration; advanced search not executed" if baseline_only else ("Validation threshold triggered bounded 4-config search" if trigger else "All top routes meet validation threshold after SARIMA")
                write_json(folder / "lightgbm_decision.json", decision)
                write_csv(folder / "validation_metrics.csv", metrics)
                write_csv(folder / "selected_models.csv", select_models(metrics, top, cfg, failed))
            elif current == "test":
                selected = pd.read_csv(folder / "selected_models.csv")
                # Selection file is sealed before this first access to test scoring.
                manifest["selection_sha256_before_test"] = sha256(folder / "selected_models.csv")
                predictions, logs = selected_backtest(daily, selected, top, cfg, progress, sales=sales)
                predictions["run_id"] = run_id
                metrics = metric_table(predictions[predictions.split.eq("test")])
                write_csv(folder / "predictions.csv", predictions)
                write_csv(folder / "metrics.csv", metrics)
                write_csv(folder / "test_log.csv", logs)
                write_csv(folder / "accuracy_acceptance.csv", acceptance(metrics, top, cfg))
                if sha256(folder / "selected_models.csv") != manifest["selection_sha256_before_test"]:
                    raise ValueError("Selection changed after test access")
            elif current == "forecast":
                selected = pd.read_csv(folder / "selected_models.csv")
                latest = forecast_at(daily, selected, top, cfg["forecast_origin"], cfg, progress, sales=sales)
                demo_forecast = forecast_at(daily, selected, top, cfg["demo_origin"], cfg, progress, sales=sales)
                latest["run_id"] = run_id; demo_forecast["run_id"] = run_id
                write_csv(folder / "forecast.csv", latest)
                write_csv(folder / "demo_forecast.csv", demo_forecast)
            elif current == "inventory":
                predictions = read_predictions(folder / "predictions.csv")
                latest = read_predictions(folder / "forecast.csv")
                forecast_table = pd.concat([predictions, latest], ignore_index=True)
                matrix = item_matrix(sales, cfg)
                progress('Prepare shared causal SKU allocations')
                allocation_plan = AllocationPlan(matrix, forecast_table, cfg)
                policy_summaries, issues = [], []
                alerts = replay_alerts(matrix, forecast_table, cfg)
                scenarios = [(cfg, s) for s in cfg["stress_scenarios"]]
                base = cfg["stress_scenarios"][0]
                for cover in [3, 14]:
                    modified = copy.deepcopy(cfg); modified["inventory"]["initial_cover_days"] = cover
                    scenarios.append((modified, {**base, "name": f"sensitivity_cover_{cover}"}))
                for lead in [1, 7]:
                    modified = copy.deepcopy(cfg)
                    for params in modified["inventory"]["partners"].values(): params["lead_time_days"] = lead
                    scenarios.append((modified, {**base, "name": f"sensitivity_lead_{lead}"}))
                for multiplier in [0.5, 1.5]:
                    modified = copy.deepcopy(cfg)
                    for params in modified["inventory"]["partners"].values(): params["safety_days"] *= multiplier
                    scenarios.append((modified, {**base, "name": f"sensitivity_safety_{multiplier}"}))
                transactions = prepare_transactions(sales, cfg)
                with (folder / 'inventory_events.csv.tmp').open('w', encoding='utf-8', newline='') as stream:
                    event_writer = csv.DictWriter(stream, fieldnames=EVENT_COLUMNS)
                    event_writer.writeheader()
                    for index, (modified, scenario) in enumerate(scenarios):
                        ledger, rec, issue = run_policy(matrix, forecast_table, modified, scenario, progress,
                                                       transactions=transactions, event_writer=event_writer,
                                                       allocation_plan=allocation_plan)
                        mode = "w" if index == 0 else "a"
                        ledger.to_csv(folder / "inventory_ledger.csv.tmp", mode=mode, header=index == 0, index=False)
                        rec.to_csv(folder / "inventory_recommendations.csv.tmp", mode=mode, header=index == 0, index=False)
                        policy_summaries.append(simulation_metrics(ledger, alerts).iloc[:1])
                        issues.append(issue)
                for name in ["inventory_ledger", "inventory_recommendations", 'inventory_events']:
                    (folder / f"{name}.csv.tmp").replace(folder / f"{name}.csv")
                write_csv(folder / "alerts.csv", alerts)
                write_json(folder / 'alert_opportunity_diagnostic.json', alert_opportunity_summary(alerts))
                issue = pd.concat(issues, ignore_index=True)
                if issue.empty: issue = pd.DataFrame(columns=ROUTE + ["as_of_date", "scenario_id", "status"])
                write_csv(folder / "inventory_issues.csv", issue)
                replay_summary = simulation_metrics(ledger, alerts).iloc[-1:]
                write_csv(folder / "simulation_metrics.csv", pd.concat(policy_summaries + [replay_summary], ignore_index=True))
                write_json(folder / "scenario_configs.json", [{"scenario": scenario, "inventory": modified["inventory"]} for modified, scenario in scenarios])
                write_json(folder / "ledger_method.json", {
                    "granularity": "chronological receipt/sale events plus item-day balances", "receipt_timing": "beginning of UTC day", "order_decision": "end of UTC day",
                    "sale_order": "order_datetime UTC, then order_id; receipt events precede same-time sales",
                    "stress_apportionment": "Exact largest remainders per item-day; chronological ties; historical quantity unchanged",
                    "private_event_output": "inventory_events.csv contains order_id and stays local; dashboard does not export it",
                    "partial_receipt": "unreceived portion is canceled at actual receipt; no invented backorder",
                    "delayed_receipt": "delay revealed when promised ETA becomes overdue",
                    "real_inventory_data": False,
                })
            manifest["stages"][current] = "complete"
            manifest["status"] = "partial"
            seal_manifest(folder, manifest)
        if all(manifest["stages"].get(s) == "complete" for s in STAGES):
            manifest["status"] = "complete"
            result = pd.read_csv(folder / "accuracy_acceptance.csv")
            manifest["accuracy_criterion_passed"] = bool(result.accuracy_passed.all())
            manifest["acceptance_note"] = "Software run complete; accuracy criterion evaluated separately; reports/slides deferred"
        if sha256(source) != audit["source_sha256_before"]:
            raise ValueError("Source hash changed")
        seal_manifest(folder, manifest)
        progress(f"Run: {run_id}; status: {manifest['status']}")
        return folder
    except Exception as error:
        manifest["status"] = "failed"
        manifest["stages"][current] = "failed"
        manifest["error_type"] = type(error).__name__
        seal_manifest(folder, manifest)
        # Do not include source record content in public logs or errors.
        raise


def main():
    parser = argparse.ArgumentParser(description="SIGMA local sales forecasting and simulated inventory")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--stage", choices=STAGES + ["all"], default="all")
    parser.add_argument("--run-id")
    parser.add_argument("--demo", action="store_true", help="Generate only synthetic orders for an independent demonstration")
    parser.add_argument("--baseline-only", action="store_true", help="MVP/demo only; does not claim SARIMA/LightGBM executed")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument('--validation-cache-run', help='Import sealed historical validation evidence explicitly; run new candidates fresh')
    args = parser.parse_args()
    try:
        execute(args.config, args.stage, args.run_id, args.demo, args.baseline_only, args.resume, args.validation_cache_run)
    except Exception as error:
        detail = str(error) if isinstance(error, DataQualityError) else "Check local manifest/configuration; source preserved"
        print(f"Pipeline stopped: {type(error).__name__}. {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
