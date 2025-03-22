import json

from main import app
from typer.testing import CliRunner


def test_check_gh_probe_fails():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing GitHub probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        # FIXME: switch probe back to main branch
        "github://canonical/juju-doctor//tests/resources/probes/python/failing.py?feat/ruleset",
        "--status",
        "tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    check = json.loads(result.stdout)
    assert check == {"failed": 3, "passed": 0}
