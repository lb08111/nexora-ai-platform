# -*- coding: utf-8 -*-
"""Eval gate: the scripted session must clear every threshold."""
from __future__ import annotations

import pytest

from eval_session import METRIC_THRESHOLDS, run_eval


@pytest.mark.unit
def test_eval_passes_all_thresholds():
    report = run_eval()
    assert report.passed, (
        "discovery-copilotkit eval thresholds failed:\n  - "
        + "\n  - ".join(report.failures)
        + f"\nmetrics={report.metrics}"
    )


def test_eval_emits_blueprint_when_done():
    report = run_eval()
    assert report.metrics.turn_count >= 1
    assert report.metrics.blueprint_team_size >= 1
    assert report.metrics.blueprint_integrations >= 1


def test_eval_renders_full_component_set():
    report = run_eval()
    # Scripted session covers every component except possibly OpenAreasList
    # (the scripted session does not push areas), so coverage must be at
    # least 4/5 — keeping the floor matches the threshold but pins the
    # exact slices that lit up so we notice if the manifest drifts.
    assert "CompanyProfileCard" in report.metrics.rendered_components
    assert "IntegrationsList" in report.metrics.rendered_components
    assert "BlueprintPreview" in report.metrics.rendered_components
    assert "DiscoveryAgentPanel" in report.metrics.rendered_components


def test_eval_report_serialises_to_json():
    report = run_eval()
    d = report.to_dict()
    assert d["passed"] is True
    assert d["thresholds"] == METRIC_THRESHOLDS
    assert "metrics" in d and "transcript" in d
