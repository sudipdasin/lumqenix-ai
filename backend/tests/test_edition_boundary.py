"""Regression tests for public/private source separation."""
import importlib.util
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[2] / "scripts" / "check_edition_boundary.py"
spec = importlib.util.spec_from_file_location("edition_boundary", CHECKER)
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


@pytest.mark.parametrize("path", [
    "proprietary/engine.py", "premium/features.py", "private/key",
    "commercial/license.py", "secrets/token", "licenses/keys/key.pem",
    "backend/models/proprietary/weights.bin", "frontend/pro/dashboard.js",
    "backend/app/premium/api.py", "../outside.txt", "/etc/passwd",
    "Proprietary/algorithm.py", "private" + chr(92) + "key.txt",
])
def test_reject_private_paths(path):
    assert boundary.forbidden_paths([path]) == [path]


@pytest.mark.parametrize("path", [
    "backend/app/main.py", "frontend/index.html",
    "docs/COMMUNITY_PRO_STRATEGY.md", "backend/models/pretrained.json",
    "scripts/check_edition_boundary.py",
])
def test_allow_community_paths(path):
    assert boundary.forbidden_paths([path]) == []


def test_collects_all_violations():
    assert boundary.forbidden_paths(
        ["README.md", "private/a", "premium/b"]
    ) == ["private/a", "premium/b"]
