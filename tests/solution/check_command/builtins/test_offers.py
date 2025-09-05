import json

from typer.testing import CliRunner

from juju_doctor.main import app


def test_builtin_failing():
    # GIVEN a RuleSet with failing Offers assertions
    runner = CliRunner()
    test_args = [
        "check",
        "--verbose",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/invalid/builtins/offers/failing.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    exceptions = json.loads(result.stdout)["exceptions"]
    # AND the user is warned of their Offers mistakes
    assert any(
        "Not all offers: ['loki-logging-fake', 'loki-logging', 'loki-logging'] were found in" in e
        for e in exceptions
    )
    assert any(
        "loki-logging: endpoint (logging-fake) not in (dict_keys(['logging']))" in e
        for e in exceptions
    )
    assert any(
        "loki-logging: interface (loki_push_api_fake) != (loki_push_api)" in e for e in exceptions
    )
    # AND they are all identified as failing
    assert json.loads(result.stdout)["failed"] == 3
    assert json.loads(result.stdout)["passed"] == 0
