import json

from typer.testing import CliRunner

from juju_doctor.main import app


def test_builtins_failing():
    # GIVEN a RuleSet with failing Builtin assertions
    runner = CliRunner()
    test_args = [
        "check",
        "--verbose",
        "--format=json",
        "--probe=file://tests/resources/probes/ruleset/invalid/builtins-failing.yaml",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    exceptions = json.loads(result.stdout)["exceptions"]
    # AND the user is warned of their Builtin Applications mistakes
    assert any(
        "Not all apps: ['alertmanager_fake', 'alertmanager', 'alertmanager'] were found in" in e
        for e in exceptions
    )
    assert any("alertmanager scale (1) is below the allowable limit: 2" in e for e in exceptions)
    assert any("alertmanager scale (1) exceeds the allowable limit: 0" in e for e in exceptions)
    # AND the user is warned of their Builtin Relations mistakes
    assert any(
        "Relation (['loki:alertmanager', 'alertmanager_fake:alerting']) not found in" in e
        for e in exceptions
    )
    assert any(
        "Relation (['loki_fake:alertmanager', 'alertmanager:alerting']) not found in" in e
        for e in exceptions
    )
    # AND the user is warned of their Builtin Offers mistakes
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
    assert json.loads(result.stdout)["failed"] == 8
    assert json.loads(result.stdout)["passed"] == 0


def test_builtins_with_invalid_schema(caplog):
    # GIVEN RuleSet Builtin assertions with invalid schemas
    runner = CliRunner()
    test_args = [
        "check",
        "--probe=file://tests/resources/probes/ruleset/invalid/builtins-invalid-schema.yaml",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
    ]
    # WHEN `juju-doctor check` is executed
    with caplog.at_level("ERROR"):
        result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the user is warned of their mistakes
    assert caplog.text.count("Failed to validate schema") == 3
