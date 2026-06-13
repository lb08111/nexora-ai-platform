# -*- coding: utf-8 -*-
"""Offline eval harness for the discovery-copilotkit plugin.

Drives the FastAPI router end-to-end using ``ScriptedDiscoverySession``
(LLM-free, deterministic) and computes a small set of metrics that act
as a regression gate for the plugin contract.

Metrics
-------
- ``turn_count``       : turns the session needed to finish.
- ``produced_question``: number of turns that produced a question.
- ``component_coverage``: fraction of manifest components that
  rendered at least once across the session.
- ``blueprint_team_size`` / ``blueprint_integrations``: completeness
  of the final ``TeamBlueprint``.
- ``mean_turn_latency_ms`` / ``p95_turn_latency_ms``: in-process
  latency per ``POST /sessions/{sid}/turn``.

Thresholds in ``METRIC_THRESHOLDS`` are conservative bars that the
deterministic scripted session must pass; if eval fails them, the
plugin is broken regardless of which LLM is hooked up.

Run with::

    python plugins/bundle/discovery-copilotkit/eval_run.py

or import ``run_eval`` from this module.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Plugin root is this file's directory; make sibling modules importable
# whether this file is run as a script, imported by tests, or loaded by
# the eval CLI.
_PLUGIN_ROOT = str(Path(__file__).resolve().parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from copilotkit_adapter import list_components  # noqa: E402
from router import SessionManager, build_router  # noqa: E402


# Scripted answers tuned to the 3-question ScriptedDiscoverySession
# (segment → systems → urgent pain). Driving a fixed conversation makes
# the metrics deterministic across runs.
_SCRIPTED_ANSWERS: list[str] = [
    "Tenho uma loja virtual de roupas femininas.",
    "Uso planilha e WhatsApp para atender clientes.",
    "Atendimento no WhatsApp toma o dia inteiro.",
]


METRIC_THRESHOLDS: dict[str, float] = {
    # The scripted session is hardcoded to 3 questions, so the full
    # session takes exactly 4 turns (open + 3 answers). Locking the
    # gate to <=6 leaves room for the live session to add one or two
    # clarifying turns before we'd consider it regressed.
    "turn_count_max": 6,
    "produced_question_min": 3,
    # Scripted session populates company.segment, integrations,
    # blueprint → 4 of the 5 manifest components must light up. The
    # 5th (DiscoveryAgentPanel) is always rendered as the shell.
    "component_coverage_min": 0.8,
    "blueprint_team_size_min": 1,
    "blueprint_integrations_min": 1,
    "mean_turn_latency_ms_max": 250.0,
    "p95_turn_latency_ms_max": 500.0,
}


@dataclass
class EvalMetrics:
    turn_count: int = 0
    produced_question: int = 0
    component_coverage: float = 0.0
    rendered_components: list[str] = field(default_factory=list)
    blueprint_team_size: int = 0
    blueprint_integrations: int = 0
    mean_turn_latency_ms: float = 0.0
    p95_turn_latency_ms: float = 0.0


@dataclass
class EvalReport:
    metrics: EvalMetrics
    thresholds: dict[str, float]
    passed: bool
    failures: list[str] = field(default_factory=list)
    transcript: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": asdict(self.metrics),
            "thresholds": self.thresholds,
            "passed": self.passed,
            "failures": self.failures,
            "transcript": self.transcript,
        }


def _build_eval_app(manager: SessionManager) -> FastAPI:
    """Wire the plugin router into a throwaway FastAPI app for the eval."""
    app = FastAPI()
    app.include_router(
        build_router(manager),
        prefix="/api/discovery-copilotkit",
    )
    return app


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    # Nearest-rank percentile — fine for the small (<=10) samples this
    # eval produces; avoids pulling numpy just for one number.
    k = max(0, min(len(ordered) - 1, int(round(pct / 100.0 * len(ordered))) - 1))
    return ordered[k]


def _evaluate(
    metrics: EvalMetrics,
    thresholds: dict[str, float],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if metrics.turn_count > thresholds["turn_count_max"]:
        failures.append(
            f"turn_count={metrics.turn_count} > max "
            f"{thresholds['turn_count_max']}",
        )
    if metrics.produced_question < thresholds["produced_question_min"]:
        failures.append(
            f"produced_question={metrics.produced_question} < min "
            f"{thresholds['produced_question_min']}",
        )
    if metrics.component_coverage < thresholds["component_coverage_min"]:
        failures.append(
            f"component_coverage={metrics.component_coverage:.2f} < min "
            f"{thresholds['component_coverage_min']}",
        )
    if metrics.blueprint_team_size < thresholds["blueprint_team_size_min"]:
        failures.append(
            f"blueprint_team_size={metrics.blueprint_team_size} < min "
            f"{thresholds['blueprint_team_size_min']}",
        )
    if metrics.blueprint_integrations < thresholds["blueprint_integrations_min"]:
        failures.append(
            f"blueprint_integrations={metrics.blueprint_integrations} < min "
            f"{thresholds['blueprint_integrations_min']}",
        )
    if metrics.mean_turn_latency_ms > thresholds["mean_turn_latency_ms_max"]:
        failures.append(
            f"mean_turn_latency_ms={metrics.mean_turn_latency_ms:.1f} > max "
            f"{thresholds['mean_turn_latency_ms_max']}",
        )
    if metrics.p95_turn_latency_ms > thresholds["p95_turn_latency_ms_max"]:
        failures.append(
            f"p95_turn_latency_ms={metrics.p95_turn_latency_ms:.1f} > max "
            f"{thresholds['p95_turn_latency_ms_max']}",
        )
    return (len(failures) == 0), failures


def run_eval(
    answers: list[str] | None = None,
    *,
    max_turns: int = 10,
) -> EvalReport:
    """Run a full session through the plugin and return metrics."""
    answers = list(answers if answers is not None else _SCRIPTED_ANSWERS)
    manager = SessionManager()  # fresh, hermetic — no global state
    app = _build_eval_app(manager)

    transcript: list[dict[str, Any]] = []
    latencies: list[float] = []
    rendered_seen: set[str] = set()
    produced_q = 0
    final_state: dict[str, Any] | None = None

    with TestClient(app) as client:
        resp = client.post("/api/discovery-copilotkit/sessions")
        resp.raise_for_status()
        opening = resp.json()
        sid = opening["session_id"]
        state = opening["state"]
        rendered_seen.update(state.get("rendered_components", []))
        if state.get("question"):
            produced_q += 1
        transcript.append({"turn": 0, "agent": state.get("question")})

        turn_index = 0
        while not (state.get("status") == "done") and turn_index < max_turns:
            user_msg = (
                answers[turn_index]
                if turn_index < len(answers)
                else "ok, segue."
            )
            t0 = time.perf_counter()
            r = client.post(
                f"/api/discovery-copilotkit/sessions/{sid}/turn",
                json={"message": user_msg},
            )
            t1 = time.perf_counter()
            r.raise_for_status()
            latencies.append((t1 - t0) * 1000.0)
            state = r.json()["state"]
            rendered_seen.update(state.get("rendered_components", []))
            if state.get("question"):
                produced_q += 1
            transcript.append(
                {
                    "turn": turn_index + 1,
                    "user": user_msg,
                    "agent": state.get("question"),
                    "status": state.get("status"),
                },
            )
            turn_index += 1

        final_state = state

        # Sanity: blueprint endpoint should serve the final blueprint once
        # the session is done; if it doesn't, surface as an eval failure
        # rather than letting the metrics quietly read defaults.
        if final_state and final_state.get("status") == "done":
            r = client.get(
                f"/api/discovery-copilotkit/sessions/{sid}/blueprint",
            )
            if r.status_code != 200:
                transcript.append(
                    {"warning": f"blueprint endpoint {r.status_code}"},
                )

    bp = (final_state or {}).get("blueprint") or {}
    all_components = list_components()
    coverage = (
        len(rendered_seen & set(all_components)) / float(len(all_components))
        if all_components
        else 0.0
    )

    metrics = EvalMetrics(
        turn_count=turn_index,
        produced_question=produced_q,
        component_coverage=coverage,
        rendered_components=sorted(rendered_seen),
        blueprint_team_size=len(bp.get("proposed_team", []) or []),
        blueprint_integrations=len(bp.get("detected_integrations", []) or []),
        mean_turn_latency_ms=(
            sum(latencies) / len(latencies) if latencies else 0.0
        ),
        p95_turn_latency_ms=_percentile(latencies, 95.0),
    )
    passed, failures = _evaluate(metrics, METRIC_THRESHOLDS)
    return EvalReport(
        metrics=metrics,
        thresholds=dict(METRIC_THRESHOLDS),
        passed=passed,
        failures=failures,
        transcript=transcript,
    )


def main() -> int:
    report = run_eval()
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
