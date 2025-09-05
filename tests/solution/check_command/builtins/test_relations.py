import json
import re

from typer.testing import CliRunner

from juju_doctor.main import app


def test_builtins_failing():
    # GIVEN a RuleSet with failing Relations assertions
    runner = CliRunner()
    test_args = [
        "check",
        "--verbose",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/invalid/builtins/relations/failing.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    exceptions = json.loads(result.stdout)["exceptions"]
    # AND the user is warned of their Relations mistakes
    assert any(
        "Relation (['alertmanager_fake:alerting', 'loki:alertmanager']) not found in" in e
        for e in exceptions
    )
    assert any(
        "Relation (['alertmanager:alerting', 'loki_fake:alertmanager']) not found in" in e
        for e in exceptions
    )
    # AND they are all identified as failing
    assert json.loads(result.stdout)["failed"] == 2
    assert json.loads(result.stdout)["passed"] == 0
