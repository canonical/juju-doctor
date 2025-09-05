from typer.testing import CliRunner

from juju_doctor.main import app


# TODO clean up this copy pasta
def test_builtins_failing():
    # GIVEN a RuleSet with failing Builtin assertions
    runner = CliRunner()
    test_args = [
        "schema",
        "--stdout",
    ]
    # WHEN `juju-doctor check` is executed
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # TODO: If we want to keep this command, then
    # TODO: Add a test for --file
    assert False
