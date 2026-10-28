from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"


def test_ci_runs_pytest_tsc_vitest_and_schema_check_without_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["permissions"] == {"contents": "read"}
    triggers = data.get("on", data.get(True))
    assert "push" in triggers and "pull_request" in triggers
    for command in ("pytest", "npm ci", "npx tsc --noEmit", "npx vitest run", "npm run check-schema", 'pip install -e "pipeline[dev]"'):
        assert command in text
    assert "secrets." not in text
