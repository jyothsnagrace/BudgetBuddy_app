from __future__ import annotations

from pathlib import Path

from backend.cafe_evaluation import run_evaluation_suite


def test_cafe_evaluation_suite_generates_reports(tmp_path: Path) -> None:
    workspace_root = tmp_path
    (workspace_root / "docs").mkdir(parents=True, exist_ok=True)
    (workspace_root / "backend" / "rag_cache").mkdir(parents=True, exist_ok=True)

    payload = run_evaluation_suite(str(workspace_root))

    assert "overall_score" in payload
    assert 0.0 <= float(payload["overall_score"]) <= 1.0

    ab_test = payload["ab_test"]
    assert "system_metrics" in ab_test and "baseline_metrics" in ab_test

    for metric_name in ["accuracy", "relevance", "coherence", "faithfulness"]:
        assert metric_name in ab_test["system_metrics"]

    scenario_names = {s["name"] for s in payload["scenarios"]}
    assert {"happy_path", "corrupted_memory_recovery", "long_nested_context", "no_api_key_mode"}.issubset(
        scenario_names
    )

    assert (workspace_root / "docs" / "cafe_evaluation_results.json").exists()
    assert (workspace_root / "docs" / "CAFE_EVALUATION_REPORT.md").exists()
    assert (workspace_root / "docs" / "cafe_human_eval_template.csv").exists()
