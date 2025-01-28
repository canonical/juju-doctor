from typer.testing import CliRunner

# TODO app requires src.fetcher lib
from src.main import app


def test_check_with_probes():
    runner = CliRunner()
    test_args = [
            "check",
            "--format",
            "json",
            "--probe",
            "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py",
            "--show-unit",
            "resources/bundle/gagent-bundle.yaml",
        ]
    result = runner.invoke(app,test_args)
    assert result.exit_code == 0
    # Use result.stdout to access the command's output
    assert result.stdout == "something"
