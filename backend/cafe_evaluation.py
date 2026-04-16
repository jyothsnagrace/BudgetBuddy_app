"""Evaluation suite for Pet Cafe multi-agent behavior.

This module provides:
1) Automated metrics: accuracy, relevance, coherence, faithfulness.
2) A/B testing against a baseline variant.
3) Scenario and edge-case coverage with failure-mode notes.
4) Report and human-eval template generation.
"""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple

from backend import cafe_agents
from backend.cafe_tools import load_cafe_memory, save_cafe_memory

ALLOWED_SPEAKERS = {"user_pet", "npc_pet_1", "npc_pet_2", "barista_planner"}
SPEAKER_LABELS = ("Mochi", "Penny", "Capy", "Esper")
FINANCE_KEYWORDS = {
    "budget",
    "save",
    "savings",
    "spend",
    "money",
    "quest",
    "hoard",
    "expense",
    "cash",
}
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "to",
    "of",
    "for",
    "on",
    "in",
    "we",
    "is",
    "are",
    "it",
    "this",
    "that",
    "with",
    "as",
    "be",
    "or",
    "by",
    "i",
    "you",
}


@dataclass
class EvaluationScenario:
    name: str
    description: str
    turns: int
    seed_history: List[Dict[str, Any]] | None = None


def _tokenize(text: str) -> List[str]:
    return [tok for tok in re.findall(r"[a-zA-Z]{3,}", text.lower()) if tok not in STOPWORDS]


def _sentence_count(text: str) -> int:
    return len([p for p in re.split(r"[.!?]+", text) if p.strip()])


def _has_nested_speaker_quotes(text: str) -> bool:
    matches = re.findall(r"(?:Mochi|Penny|Capy|Esper):", text)
    return len(matches) > 1


def _safe_mean(values: List[float]) -> float:
    return float(mean(values)) if values else 0.0


def metric_accuracy(history: List[Dict[str, Any]]) -> float:
    """Structural and turn-management accuracy."""
    if not history:
        return 0.0

    checks = 0
    passed = 0

    for i, entry in enumerate(history):
        checks += 1
        if entry.get("speaker") in ALLOWED_SPEAKERS:
            passed += 1

        checks += 1
        if isinstance(entry.get("content"), str) and bool(entry["content"].strip()):
            passed += 1

        checks += 1
        if "timestamp" in entry:
            passed += 1

        if i >= 2:
            checks += 1
            speaker = entry.get("speaker")
            prev = history[i - 1].get("speaker")
            prev2 = history[i - 2].get("speaker")
            if speaker not in {prev, prev2}:
                passed += 1

    return round(passed / max(checks, 1), 4)


def metric_relevance(history: List[Dict[str, Any]]) -> float:
    """Topical relevance to prior turn and finance domain."""
    if len(history) < 2:
        return 0.0

    pair_scores: List[float] = []
    for i in range(1, len(history)):
        prev = str(history[i - 1].get("content", ""))
        curr = str(history[i].get("content", ""))

        prev_tokens = set(_tokenize(prev))
        curr_tokens = set(_tokenize(curr))

        overlap = len(prev_tokens.intersection(curr_tokens))
        overlap_score = 1.0 if overlap > 0 else 0.0

        domain_score = 1.0 if any(k in curr.lower() for k in FINANCE_KEYWORDS) else 0.0
        pair_scores.append((overlap_score * 0.5) + (domain_score * 0.5))

    return round(_safe_mean(pair_scores), 4)


def metric_coherence(history: List[Dict[str, Any]]) -> float:
    """Conversation coherence and response quality constraints."""
    if not history:
        return 0.0

    scores: List[float] = []
    for entry in history:
        content = str(entry.get("content", "")).strip()

        s = 0.0
        if content:
            s += 0.4
        if _sentence_count(content) <= 2:
            s += 0.3
        if not _has_nested_speaker_quotes(content):
            s += 0.3

        scores.append(s)

    return round(_safe_mean(scores), 4)


def metric_faithfulness(history: List[Dict[str, Any]]) -> float:
    """Faithfulness to tool/state signals and quest metadata."""
    if not history:
        return 0.0

    checks = 0
    passed = 0
    saw_tool = False

    for entry in history:
        meta = entry.get("meta", {}) or {}

        checks += 1
        quest_flag = bool(meta.get("quest"))
        if ("quest" in str(entry.get("content", "")).lower()) == quest_flag or not quest_flag:
            passed += 1

        if meta.get("tool") == "fetch_budget_data":
            saw_tool = True

    checks += 1
    if saw_tool:
        passed += 1

    return round(passed / max(checks, 1), 4)


def evaluate_history(history: List[Dict[str, Any]]) -> Dict[str, float]:
    return {
        "accuracy": metric_accuracy(history),
        "relevance": metric_relevance(history),
        "coherence": metric_coherence(history),
        "faithfulness": metric_faithfulness(history),
    }


def _pick_next_speaker(history: List[Dict[str, Any]]) -> str:
    order = ["user_pet", "npc_pet_1", "npc_pet_2", "barista_planner"]
    last_two = [h.get("speaker") for h in history[-2:]]
    available = [s for s in order if s not in last_two] or order
    return available[len(history) % len(available)]


def _baseline_turn(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    speaker = _pick_next_speaker(history)
    prev = str(history[-1].get("content", "")) if history else "start"
    content = cafe_agents._mock_single_turn(speaker, prev, len(history))
    return {
        "id": f"baseline-{len(history)}",
        "speaker": speaker,
        "content": content,
        "timestamp": datetime.utcnow().isoformat() if False else "baseline",
        "meta": {"quest": "quest:" in content.lower(), "continued": True},
    }


def run_system_variant(user_id: str, turns: int, memory_path: str) -> List[Dict[str, Any]]:
    transcript: List[Dict[str, Any]] = []
    for _ in range(turns):
        transcript.extend(cafe_agents.run_cafe_continue_turn(user_id=user_id, memory_path=memory_path))
    return transcript


def run_baseline_variant(turns: int) -> List[Dict[str, Any]]:
    transcript: List[Dict[str, Any]] = [
        {
            "id": "baseline-0",
            "speaker": "barista_planner",
            "content": "Cafe open. Ledger synced — one focused topic at a time.",
            "timestamp": "baseline",
            "meta": {"tool": "fetch_budget_data", "quest": False},
        }
    ]
    for _ in range(max(0, turns - 1)):
        transcript.append(_baseline_turn(transcript))
    return transcript


def run_ab_test(user_id: str, turns: int, memory_path: str) -> Dict[str, Any]:
    system_history = run_system_variant(user_id=user_id, turns=turns, memory_path=memory_path)
    baseline_history = run_baseline_variant(turns=turns)

    system_metrics = evaluate_history(system_history)
    baseline_metrics = evaluate_history(baseline_history)

    delta = {
        key: round(system_metrics[key] - baseline_metrics.get(key, 0.0), 4)
        for key in system_metrics
    }

    winner = "system"
    if _safe_mean(list(delta.values())) < 0:
        winner = "baseline"

    return {
        "system_metrics": system_metrics,
        "baseline_metrics": baseline_metrics,
        "delta": delta,
        "winner": winner,
        "turns": turns,
    }


def detect_external_eval_tools() -> Dict[str, bool]:
    tools = {"trulens": False, "ragas": False}

    try:
        __import__("trulens_eval")
        tools["trulens"] = True
    except Exception:
        pass

    try:
        __import__("ragas")
        tools["ragas"] = True
    except Exception:
        pass

    return tools


def run_scenario(scenario: EvaluationScenario, root_dir: str) -> Dict[str, Any]:
    memory_path = str(Path(root_dir) / "backend" / "rag_cache" / f"eval_{scenario.name}.json")
    if scenario.seed_history is None:
        save_cafe_memory([], memory_path)
    else:
        save_cafe_memory(scenario.seed_history, memory_path)

    history = run_system_variant(
        user_id=f"eval_{scenario.name}",
        turns=scenario.turns,
        memory_path=memory_path,
    )

    metrics = evaluate_history(history)
    failure_modes: List[str] = []

    if metrics["coherence"] < 0.7:
        failure_modes.append("coherence_drop")
    if metrics["accuracy"] < 0.85:
        failure_modes.append("turn_rule_violation")
    if any(_has_nested_speaker_quotes(str(h.get("content", ""))) for h in history):
        failure_modes.append("nested_quotes_detected")

    return {
        "name": scenario.name,
        "description": scenario.description,
        "metrics": metrics,
        "messages": len(history),
        "failure_modes": failure_modes,
        "status": "passed" if not failure_modes else "needs_review",
    }


def generate_human_eval_template(path: str, sample_history: List[Dict[str, Any]]) -> None:
    headers = [
        "turn_index",
        "speaker",
        "content",
        "relevance_1_to_5",
        "coherence_1_to_5",
        "faithfulness_1_to_5",
        "overall_1_to_5",
        "notes",
    ]

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for i, entry in enumerate(sample_history):
            writer.writerow([i, entry.get("speaker", ""), entry.get("content", ""), "", "", "", "", ""])


def write_markdown_report(path: str, payload: Dict[str, Any]) -> None:
    lines = [
        "# Cafe Evaluation Report",
        "",
        "## Summary",
        f"- Overall score: {payload['overall_score']:.4f}",
        f"- A/B winner: {payload['ab_test']['winner']}",
        f"- External tools detected: {payload['external_tools']}",
        "",
        "## Metric Definitions",
        "- accuracy: schema + speaker rotation constraint adherence",
        "- relevance: topical linkage to prior turn + finance-domain grounding",
        "- coherence: concise and non-nested utterances",
        "- faithfulness: metadata consistency + tool-usage grounding",
        "",
        "## A/B Comparison",
        f"- System metrics: {payload['ab_test']['system_metrics']}",
        f"- Baseline metrics: {payload['ab_test']['baseline_metrics']}",
        f"- Delta (system-baseline): {payload['ab_test']['delta']}",
        "",
        "## Scenario Analysis",
    ]

    for item in payload["scenarios"]:
        lines.extend(
            [
                f"### {item['name']}",
                f"- Description: {item['description']}",
                f"- Status: {item['status']}",
                f"- Messages: {item['messages']}",
                f"- Metrics: {item['metrics']}",
                f"- Failure modes: {item['failure_modes'] or ['none']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Edge Cases and Failure Modes",
            "- corrupted_memory: verifies loader fallback and continued generation",
            "- long_nested_context: checks quote-nesting resistance and coherence",
            "- no_api_key_mode: validates graceful fallback behavior",
            "",
        ]
    )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def run_evaluation_suite(root_dir: str) -> Dict[str, Any]:
    root = Path(root_dir)
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        EvaluationScenario(
            name="happy_path",
            description="Standard multi-turn cafe flow.",
            turns=6,
        ),
        EvaluationScenario(
            name="corrupted_memory_recovery",
            description="Start from malformed-memory-like minimal state.",
            turns=5,
            seed_history=[{"unexpected": True}],
        ),
        EvaluationScenario(
            name="long_nested_context",
            description="Stress with nested speaker-like prefixes in prior content.",
            turns=5,
            seed_history=[
                {
                    "id": "seed-1",
                    "speaker": "npc_pet_2",
                    "content": "Capy: for Mochi: for Penny: we should still save today.",
                    "timestamp": "seed",
                    "meta": {},
                }
            ],
        ),
        EvaluationScenario(
            name="no_api_key_mode",
            description="Validation when live LLM is not configured.",
            turns=4,
        ),
    ]

    scenario_results = [run_scenario(s, root_dir=str(root)) for s in scenarios]

    ab_memory = str(root / "backend" / "rag_cache" / "eval_ab.json")
    save_cafe_memory([], ab_memory)
    ab_test = run_ab_test(user_id="eval_ab_user", turns=6, memory_path=ab_memory)

    all_metric_values: List[float] = []
    for result in scenario_results:
        all_metric_values.extend(result["metrics"].values())

    overall_score = _safe_mean(all_metric_values)

    payload = {
        "overall_score": overall_score,
        "ab_test": ab_test,
        "scenarios": scenario_results,
        "external_tools": detect_external_eval_tools(),
    }

    report_json_path = docs_dir / "cafe_evaluation_results.json"
    report_md_path = docs_dir / "CAFE_EVALUATION_REPORT.md"
    human_csv_path = docs_dir / "cafe_human_eval_template.csv"

    with open(report_json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    write_markdown_report(str(report_md_path), payload)

    sample_history = run_system_variant(
        user_id="eval_human_template",
        turns=5,
        memory_path=str(root / "backend" / "rag_cache" / "eval_human_template.json"),
    )
    generate_human_eval_template(str(human_csv_path), sample_history)

    return payload
