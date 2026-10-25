"""Read-only adapter to the fixed M2 implementations; no legacy run() entrypoint."""

import json
from core.settings import PROJECT_ROOT as ROOT
from src.common import ROUTE, sha256
from M2.models.registry import load_settings
from M2.models.weekly import checked_series
from M2.models.LightGBM.model import phase as lgbm_phase
from M2.models.families import ts_job
from M2.final_report import replay as final_replay


def configuration():
    cfg = json.loads((ROOT / "data/configs/config.json").read_text(encoding="utf-8"))
    settings = load_settings(ROOT / "data/configs/m2-reproduce.json")
    final = json.loads(
        (ROOT / "data/configs/m2-final.json").read_text(encoding="utf-8")
    )
    return cfg, settings, final


def top10(daily, split):
    cfg, settings, final = configuration()
    keys = {(r["destination_country"], r["carrier"]) for r in final["routes"]}
    population = daily.loc[
        [tuple(k) in keys for k in daily[ROUTE].itertuples(index=False, name=None)]
    ]
    if set(population[ROUTE].itertuples(index=False, name=None)) != keys:
        raise ValueError("Fixed M2 top10 population is incomplete")
    predictions, logs = final_replay(population, cfg, settings, final, split)
    choices = {(r["destination_country"], r["carrier"]): r for r in final["routes"]}
    for key, part in predictions.groupby(ROUTE):
        if set(part.model) != {choices[key]["model"]}:
            raise ValueError("Fixed M2 selection changed")
    return predictions, logs


def candidate_job(daily, split, family, model, routes):
    cfg, settings, _ = configuration()
    groups = checked_series(daily)
    if family == "LightGBM":
        selected = {key: groups[key].sales_qty.astype(float) for key in routes}
        # Training retains all train routes. Only emitted routes are filtered.
        frame, log = lgbm_phase(
            daily,
            selected,
            cfg,
            settings,
            "direct_7d",
            split,
            {key: model for key in routes},
        )
        return frame, log
    if family != "Prophet" or len(routes) != 1:
        raise ValueError("Prophet requires a single registered route")
    key = routes[0]
    return ts_job(
        groups[key].sales_qty.astype(float),
        key,
        "Prophet",
        "direct_7d",
        model,
        settings["models"]["Prophet"][model],
        cfg,
        settings,
        split,
    )


def specs_fingerprint():
    paths = [
        ROOT / "data/configs" / p
        for p in ["config.json", "m2-final.json", "m2-reproduce.json"]
    ]
    paths += list((ROOT / "M2/models").rglob("*.py"))
    paths += [
        ROOT / "M2/models/LightGBM/variants.json",
        ROOT / "M2/models/Prophet/variants.json",
    ]
    return {
        p.relative_to(ROOT).as_posix(): sha256(p)
        for p in sorted(paths)
        if "tests" not in p.parts
    }
