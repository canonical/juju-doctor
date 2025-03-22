import json

from main import app
from typer.testing import CliRunner


def test_check_file_probe_fails():
    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing file probe
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    check = json.loads(result.stdout)
    # AND the Probe was correctly executed
    assert check == {"failed": 3, "passed": 0}
