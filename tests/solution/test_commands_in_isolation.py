import json


# https://github.com/fastapi/typer/discussions/1259
def test_1(runner, app_fixture):
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/passing.py",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    result = runner.invoke(app_fixture, test_args)
    assert len(json.loads(result.stdout)["Results"]["children"]) == 1 # Now has len == 1

def test_2(runner, app_fixture):
    test_args = [
        "check",
        "--format=json",
        "--probe=file://tests/resources/probes/python/failing.py",
        "--status=tests/resources/artifacts/status.yaml",
        "--bundle=tests/resources/artifacts/bundle.yaml",
        "--show-unit=tests/resources/artifacts/show-unit.yaml",
    ]
    res = runner.invoke(app_fixture, test_args)
    assert len(json.loads(res.stdout)["Results"]["children"]) == 1 # Now has len == 2
