from typer.testing import CliRunner

# TODO app requires src.fetcher lib
from src.main import app


def test_check_file_probe_fails():
    runner = CliRunner()
    test_args = [
        "check",
        "--format",
        "json",
        "--probe",
        "file://tests/resources/show-unit/failing.py",
        "--show-unit",
        "tests/resources/show-unit/show-unit.yaml",
    ]
    result = runner.invoke(app, test_args)
    assert result.exit_code == 0
    # Use result.stdout to access the command's output
    assert result.stdout == "something"
