
from typer.testing import CliRunner

from juju_doctor.main import app

"""\
Results
├── Artifact
│   ├── bundle
│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)
│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed
│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed
│   │   ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle passed
│   ├── show_unit
│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)
│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed
│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed
│   │   ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit passed
│   ╰── status
│       ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)
│       ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)
│       ├── 🟢 tests_resources_probes_python_passing.py/status passed
│       ├── 🟢 tests_resources_probes_python_passing.py/status passed
│       ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status passed
├── Parent
│   ├── /tmp/tmpl6gtta4v/probes
│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)
│   │   ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)
│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed
│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed
│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed
│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed
│   │   ├── 🟢 tests_resources_probes_python_passing.py/status passed
│   │   ╰── 🟢 tests_resources_probes_python_passing.py/status passed
│   ╰── /tmp/tmpl6gtta4v/probes/tests_resources_probes_ruleset_small-dir
│       ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle passed
│       ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit passed
│       ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status passed
╰── Status
    ├── fail
    │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)
    │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)
    │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)
    │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)
    │   ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)
    │   ╰── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)
    ╰── pass
        ├── 🟢 tests_resources_probes_python_passing.py/bundle passed
        ├── 🟢 tests_resources_probes_python_passing.py/bundle passed
        ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed
        ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed
        ├── 🟢 tests_resources_probes_python_passing.py/status passed
        ├── 🟢 tests_resources_probes_python_passing.py/status passed
        ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle passed
        ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit passed
        ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status passed

Total: 🟢 9 🔴 6
"""  # noqa: E501


def test_all_ruleset_probe_result():
    result = "Results\n├── Artifact\n│   ├── bundle\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed\n│   │   ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle passed\n│   ├── show_unit\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed\n│   │   ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit passed\n│   ╰── status\n│       ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)\n│       ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)\n│       ├── 🟢 tests_resources_probes_python_passing.py/status passed\n│       ├── 🟢 tests_resources_probes_python_passing.py/status passed\n│       ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status passed\n├── Parent\n│   ├── /tmp/tmppchcrius/probes\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)\n│   │   ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/bundle passed\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed\n│   │   ├── 🟢 tests_resources_probes_python_passing.py/status passed\n│   │   ╰── 🟢 tests_resources_probes_python_passing.py/status passed\n│   ╰── /tmp/tmppchcrius/probes/tests_resources_probes_ruleset_small-dir\n│       ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle passed\n│       ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit passed\n│       ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status passed\n╰── Status\n    ├── fail\n    │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)\n    │   ├── 🔴 tests_resources_probes_python_failing.py/bundle failed (Bundle probe here, something went wro...)\n    │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)\n    │   ├── 🔴 tests_resources_probes_python_failing.py/show_unit failed (I'm the show-unit probe, bad things h...)\n    │   ├── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)\n    │   ╰── 🔴 tests_resources_probes_python_failing.py/status failed (I'm the status probe, and I failed)\n    ╰── pass\n        ├── 🟢 tests_resources_probes_python_passing.py/bundle passed\n        ├── 🟢 tests_resources_probes_python_passing.py/bundle passed\n        ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed\n        ├── 🟢 tests_resources_probes_python_passing.py/show_unit passed\n        ├── 🟢 tests_resources_probes_python_passing.py/status passed\n        ├── 🟢 tests_resources_probes_python_passing.py/status passed\n        ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle passed\n        ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit passed\n        ╰── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status passed\n\n\nTotal: 🟢 \x1b[1;36m9\x1b[0m 🔴 \x1b[1;36m6\x1b[0m\n"  # noqa: E501

    # GIVEN a CLI Typer app
    runner = CliRunner()
    # WHEN the "check" command is executed on a failing file probe
    test_args = [
        "check",
        "--format",
        "tree",
        "--probe",
        "file://tests/resources/probes/ruleset/all.yaml",
        "--status=tests/resources/artifacts/status.yaml",
    ]
    result = runner.invoke(app, test_args)
    # THEN the command succeeds
    assert result.exit_code == 0
    # AND the Probe was correctly executed
    assert result.stdout == result.stdout


if __name__ == "__main__":
    test_all_ruleset_probe_result()
