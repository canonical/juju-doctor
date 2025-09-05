import json
import re

from typer.testing import CliRunner

from juju_doctor.main import app


def test_builtin_failing():
    # GIVEN a RuleSet with failing Applications assertions
    runner = CliRunner()
    test_args = [
        "check",
        "--verbose",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/invalid/builtins/applications/failing.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    exceptions = json.loads(result.stdout)["exceptions"]
    # AND the user is warned of their Applications mistakes
    assert any(re.search(r"Not all apps:.*alertmanager_fake.*were found", e) for e in exceptions)
    assert any(re.search(r"alertmanager scale.*below.*2", e) for e in exceptions)
    assert any(re.search(r"alertmanager scale.*exceeds.*0", e) for e in exceptions)
    # AND they are all identified as failing
    assert json.loads(result.stdout)["failed"] == 3
    assert json.loads(result.stdout)["passed"] == 0
