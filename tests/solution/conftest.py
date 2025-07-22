import pytest
from typer.testing import CliRunner

from juju_doctor.main import app


@pytest.fixture(scope="function")
def runner():
    return CliRunner()


@pytest.fixture(scope="function")
def app_fixture():
    return app
