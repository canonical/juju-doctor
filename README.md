# 🩺 juju-doctor 🩺

[![PyPI](https://img.shields.io/pypi/v/juju-doctor)](https://pypi.org/project/juju-doctor/)
[![Release](https://github.com/canonical/juju-doctor/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/loki-k8s-operator/actions/workflows/release.yaml)

Run a configurable set of `probes` (assertions) against Juju deployment `artifacts`, which are the output of other tools like `juju`, `sosreport`, and `kubectl`. To enforce best practices, these probes are organized into a `ruleset`, which acts as a guide for correct deployment configurations.

## Usage

Here's some typical usage examples:

```bash
∮ juju-doctor check --help # displays the help
```

You can run `juju-doctor` against a solution archive:

```
∮ juju-doctor check \
    --probe file://tests/resources/probes/python/failing.py \
    --probe file://tests/resources/probes/python/passing.py \
    --status=status.yaml \
    --status=status.yaml
```
If you have a live deplyoment, you can also run `juju-doctor` against that:
```
∮ juju-doctor check \
    --probe file://tests/resources/probes/python/failing.py \
    --probe file://tests/resources/probes/python/passing.py \
    --model testy \
    --model testy-two
```
In either case, the output will look like so (configurable with `--format` and `--verbose`):
```
Results
├── fail
│   └── 🔴 tests_resources_probes_python_failing.py (bundle, show_unit, status)
└── pass
    └── 🟢 tests_resources_probes_python_passing.py


Total: 🟢 3 🔴 3
```

The path to a probe can also be a url:
```bash
# Run a remote probe against a live model
∮ juju-doctor check --model cos --probe github://canonical/grafana-k8s-operator//probes/some_probe.py
```

## Writing Probes

### Scriptlet
Scriptlet probes are written in Python, and can run on standardized artifacts that can be provided either as static files, or gathered from a live model.

Currently, we support the following artifacts:
- **`status`**: `juju status --format=yaml`
- **`bundle`**: `juju export-bundle`
- **`show_unit`**: `juju show-unit --format=yaml`

To write a probe, you should start by choosing an artifact. Your code will only have access to one artifact *type* at a time, but the input information can span multiple models. 

Then, write a function named after your artifact (e.g., `status`, `bundle`, etc.) that takes one `Dict` argument: the artifact of choice indexed by model name. The function should raise an exception if you want your probe to fail, explaining why it failed.

Let's look at an example.

```python
from typing import Dict

def status(juju_statuses: Dict[str, Dict]): # {'cos': juju_status_dict, ...}
    ... # do things with the Juju statuses
    if not all_good:
        raise Exception("'coconut' charm shouldn't be there!")

def bundle(juju_bundles: Dict[str, Dict]):
    ... # do things with the Juju bundles
    if not passing:
      raise Exception("who deployed the 'coconut' charm?")

def _first_check(...):
    ...

def _second_check(...):
    ...

# You can split multiple checks in functions
def show_unit(juju_show_units):
    ...
    _first_check()
    _second_check()
```

**Remember**: `juju-doctor` will only run functions that exactly match a supported artifact name, and will always pass to them a dictionary of *model name* mapped to the proper artifact.

### Ruleset
Ruleset probes are written in YAML, specifying which probes should be coordinated for a deployment validation.

Currently, we support the following probe types:
- **`scriptlet`**: A Python probe
- **`ruleset`**: A declarative deployment RuleSet

```yaml
name: A declarative deployment RuleSet
probes:
  - name: Probe - test passing
    type: scriptlet
    url: file://tests/resources/probes/python/passing.py
  - name: RuleSet - test scriptlet
    type: ruleset
    url: file://tests/resources/probes/ruleset/scriptlet.yaml
  - name: Probe - test directory (may contain scriptlets and/or rulesets)
    type: scriptlet
    url: file://tests/resources/probes/ruleset/small-dir
```

#### Builtin assertions
While scriptlet probes are an escape hatch for complex, programmatic assertions, they are not intended to assert against common model patterns. For example, scriptlet probe authors may assert that certain applications or relations exist. This repetitiveness is abstracted into Builtin assertions which follows the [RuleSet schema](schema/ruleset.json). Refer to this [RuleSet with Builtin assertions](tests/resources/probes/ruleset/builtins.yaml) as a starting point.

## Development
```bash
git clone https://github.com/canonical/juju-doctor.git
uv sync --extra=dev && source .venv/bin/activate
uv pip install -e .
juju-doctor check --help
```
