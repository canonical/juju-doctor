from main import app
from typer.testing import CliRunner


def test_check_gh_probe_fails():
    runner = CliRunner()
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "github://canonical/juju-doctor//tests/resources/show-unit/failing.py",
        "--show-unit",
        "tests/resources/show-unit/show-unit.yaml",
    ]
    result = runner.invoke(app, test_args)
    assert result.exit_code == 0
    # Use result.stdout to access the command's output
    # FIXME create a valid test
    assert result.stdout != ""
