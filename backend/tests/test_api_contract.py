"""Frontend ↔ backend contract: every endpoint the frontend calls is registered.

Guards against the "Not Found" class of failure, where the UI calls a route
(e.g. POST /api/auth/register) that the backend does not expose.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

API_JS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api.js"

# Legacy e-commerce endpoints are kept in api.js for the original pages.
CALL = re.compile(r"""(request|post)\(\s*[`"](/[^`"?]*)""")
METHOD_OVERRIDE = re.compile(r"""request\(\s*`?["']?(/[^`"'?]*)[^)]*method:\s*"(PUT|DELETE)""")


def _normalise(path: str) -> str:
    return re.sub(r"\$\{[^}]+\}", "{param}", path)


def _frontend_calls() -> set[tuple[str, str]]:
    src = API_JS.read_text(encoding="utf-8")
    calls = set()
    for line in src.splitlines():
        override = METHOD_OVERRIDE.search(line)
        if override:
            calls.add((override.group(2), _normalise(override.group(1))))
            continue
        for kind, path in CALL.findall(line):
            calls.add(("POST" if kind == "post" else "GET", _normalise(path)))
    return calls


def _backend_routes(app) -> set[tuple[str, str]]:
    out = set()
    for path, ops in app.openapi()["paths"].items():
        if not path.startswith("/api"):
            continue
        for method in ops:
            out.add((method.upper(), re.sub(r"\{[^}]+\}", "{param}", path[len("/api"):])))
    return out


@pytest.mark.skipif(not API_JS.exists(), reason="frontend sources not present")
def test_every_frontend_endpoint_exists(app):
    calls = _frontend_calls()
    assert ("POST", "/auth/register") in calls  # the parser really sees the calls
    assert len(calls) > 30
    missing = sorted(calls - _backend_routes(app))
    assert missing == []
