from typer.testing import CliRunner

from juju_doctor.main import app


def test_schema_mutually_exclusive():
    # GIVEN both the RuleSet and Builtins schemas are requested
    runner = CliRunner()
    test_args = [
        "schema",
        "--ruleset",
        "--builtins",
    ]
    # WHEN `juju-doctor schema` is executed
    result = runner.invoke(app, test_args)
    # THEN the command fails because these options are mutually exclusive
    assert result.exit_code == 2
    assert "Schemas for ruleset and builtins are mutually exclusive" in result.output


def test_schema_ruleset_output():
    # GIVEN the RuleSet schema is requested
    runner = CliRunner()
    test_args = [
        "schema",
        "--ruleset",
    ]
    # WHEN `juju-doctor schema` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds, outputting the schema
    assert result.exit_code == 0
    assert result.output

def test_schema_builtins_output():
    # GIVEN the Builtins schema is requested
    runner = CliRunner()
    test_args = [
        "schema",
        "--builtins",
    ]
    # WHEN `juju-doctor schema` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds, outputting the schema
    assert result.exit_code == 0
    assert result.output
