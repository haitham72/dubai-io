"""Shared test fixtures: synthetic Karim corpus slices only (no real data).

Hermetic layer-2 privacy screen: unit tests must never reach a real model (CLAUDE.md rule 4, B0 rules).
`privacy.sensitive.screen()` falls back to the LM Studio classifier when no `classify=` is passed; here it is
replaced by a deterministic stand-in that labels each text with its first layer-1 category, or "none".
Tests that exercise the classifier pass `classify=` explicitly (they still win). Mark a test
`@pytest.mark.live_screen` to use the real local classifier.
"""
from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "live_screen: use the real local LM Studio classifier for layer-2 screen")


@pytest.fixture(autouse=True)
def _hermetic_screen(monkeypatch, request):
    if request.node.get_closest_marker("live_screen"):
        return
    if request.module.__name__.endswith("test_privacy"):
        return  # WP-C tests the classifier itself (default + injected); they never rely on a live model
    try:
        from temporal_memory.privacy import sensitive
    except ImportError:
        return

    def fake_classifier(labels: list[str]) -> dict[str, str]:
        return {label: (sensitive.categories_hit(label) or ["none"])[0] for label in labels}

    monkeypatch.setattr(sensitive, "_lmstudio_classifier", fake_classifier)
