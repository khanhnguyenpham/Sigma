"""F4 selection lock and threshold checks, before viewing new test results."""

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from web.backend.research import forecast_postprocessing_test as runner
from web.backend.research import forecast_postprocessing_test_verification as verification


def summaries(early):
    return [dict(candidate_id="C00", valid=True, metrics=dict(early_numerator=193, event_denominator=578)),
            dict(candidate_id="S25", valid=True, metrics=dict(early_numerator=early, event_denominator=578))]


@pytest.mark.parametrize("early,met", [(260, False), (261, True)])
def test_threshold_is_261_of_578_without_reselection(early, met):
    result = runner.outcome(summaries(early), "S25", {"sha256": "synthetic-lock"})
    assert result["target_met"] is met and result["reselection"] is False
    assert result["selected_on"] == "validation" and result["parameters_sha256"] == "synthetic-lock"


@pytest.mark.parametrize("kind", ["extra", "different_candidate", "changed_denominator", "coverage"])
def test_test_matrix_cannot_be_expanded_or_used_to_reselect(kind):
    rows = summaries(261)
    if kind == "extra":
        rows.append(deepcopy(rows[-1]))
    elif kind == "different_candidate":
        rows[-1]["candidate_id"] = "R90"
    elif kind == "changed_denominator":
        rows[-1]["metrics"]["event_denominator"] = 486
    else:
        rows[-1]["valid"] = False
    with pytest.raises(ValueError):
        runner.outcome(rows, "S25", {"sha256": "synthetic-lock"})


def test_forged_F3_selection_is_rejected_before_test_source_is_opened(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        verification.load_locked_test(tmp_path)


def test_cli_has_no_candidate_or_alpha_override():
    with pytest.raises(SystemExit):
        runner.main(["test", "--f3-run", "synthetic", "--candidate", "R90"])


def test_F4_has_no_calibration_or_selection_calls_and_verifier_has_no_producer_import():
    for module in (runner, verification):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr in ("calibrate", "select_validation") for n in ast.walk(tree))
    tree = ast.parse(Path(verification.__file__).read_text(encoding="utf-8"))
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(name.startswith("modules.") or name.endswith("forecast_postprocessing_test")
                   or name.endswith("forecast_postprocessing_validation") for name in imports)
