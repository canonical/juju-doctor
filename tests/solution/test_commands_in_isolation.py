import json

import pytest
from typer.testing import CliRunner

from juju_doctor.main import app


@pytest.fixture(scope="function")
def runner():
    return CliRunner()


@pytest.fixture(scope="function")
def app_fixture():
    return app

# https://github.com/fastapi/typer/discussions/1259
def test_1(runner, app_fixture):
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/mixed.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app_fixture, test_args)
    assert json.loads(result.stdout)["Results"]["children"] == 1 # Now has len == 1

def test_2(runner, app_fixture):
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/mixed.py",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    res = runner.invoke(app_fixture, test_args)
    assert json.loads(res.stdout)["Results"]["children"] == 1 # Now has len == 2
