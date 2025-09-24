import pytest
from typer.testing import CliRunner

from juju_doctor.main import app


@pytest.mark.parametrize("_type", ("ruleset", "builtins"))
def test_schema_output(_type):
    # GIVEN the schema _type is requested
    test_args = ["schema", "--type", _type]
    # WHEN `juju-doctor schema` is executed
    result = CliRunner().invoke(app, test_args)
    # THEN the command succeeds, outputting the schema
    assert result.exit_code == 0
    assert result.output
