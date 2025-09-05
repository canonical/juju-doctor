from typer.testing import CliRunner

from juju_doctor.main import app


def test_schema_output():
    # GIVEN a RuleSet pydantic model
    runner = CliRunner()
    test_args = [
        "schema",
        "--stdout",
    ]
    # WHEN `juju-doctor schema` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds, outputting the schema
    assert result.exit_code == 0
    assert result.output
