# juju-doctor
![PyPI](https://img.shields.io/pypi/v/juju-doctor)

You deploy, we validate, you fix it :)

## Usage

Here's some typical usage examples:

```bash
∮ juju-doctor check --help # displays the help
```

You can run `juju-doctor` against a solution archive:

```
∮ juju-doctor check --verbose \
    --probe file://tests/resources/failing.py \
    --probe file://tests/resources/passing.py \
    --status=status.yaml \
    --status=status.yaml
```
If you have a live deplyoment, you can also run `juju-doctor` against that:
```
∮ juju-doctor check --verbose \
    --probe file://tests/resources/failing.py \
    --probe file://tests/resources/passing.py \
    --model testy \
    --model testy-two
```
In either case, the output will look like so (configurable with `--format`):
```
🔴 tests_resources_failing.py/bundle failed
Exception: Bundle probe here, something went wrong
🔴 tests_resources_failing.py/show_unit failed
Exception: I'm the show-unit probe, bad things happened
🔴 tests_resources_failing.py/status failed
Exception: I'm the status probe, and I failed
🟢 tests_resources_passing.py/bundle passed
🟢 tests_resources_passing.py/show_unit passed
🟢 tests_resources_passing.py/status passed
```

The path to a probe can also be a url:
```
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
- **`directory`**: A directory of probes (from the types in this list)

```yaml
name: A declarative deployment RuleSet
probes:
  - name: Local probe - passing
    type: scriptlet
    url: file://tests/resources/probes/python/passing.py
  - name: Local ruleset
    type: ruleset
    url: file://tests/resources/probes/ruleset/ruleset.yaml
  - name: Local probe directory (may contain scriptlets and/or rulesets)
    type: directory
    url: file://tests/resources/probes/ruleset/small-dir
```

## Development
```bash
git clone https://github.com/canonical/juju-doctor.git
uv sync --extra=dev && source .venv/bin/activate
uv pip install -e .
juju-doctor check --help
```
