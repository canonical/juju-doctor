# juju-doctor
> You deploy, we validate, you fix :)

## Probes
Run a sample show-unit probe with:

1. On a live model
`juju show-unit grafana/0 | ./resources/relation_dashboard_uid.py`
2. On a file
`cat resources/show-unit.yaml | ./resources/relation_dashboard_uid.py`

Run that same probe with `juju-doctor`:
1. On a live model
```
juju-doctor check \
    --probe "file://tests/resources/show-unit/relation_dashboard_uid.py" \
    --model "grafana"
```
2. On a file
```
juju-doctor check \
    --probe "file://tests/resources/show-unit/relation_dashboard_uid.py" \
    --show-unit "tests/resources/show-unit/show-unit.yaml"
```
> If you want to see more internals, go to src/main.py and change the log level to INFO

### Simplest Probe
```python
#!/usr/bin/env python3

import sys
import yaml

def demo_probe(juju_artifact: dict):
    # Your validation goes here
    failure = "you_choose"
    if failure:
        print("failed", file=sys.stderr)
        exit(1)

if __name__ == "__main__":
    juju_artifact = yaml.safe_load(sys.stdin.read())
    demo_probe(juju_artifact)
```

## Demo juju-doctor commands
```
juju-doctor check --help

juju-doctor check \
    --probe "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py" \
    --model "cos"

juju-doctor check \
    --probe "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py" \
    --show-unit "tests/resources/show-unit/show-unit.yaml"

juju-doctor check \
    --probe "file://tests/resources/show-unit/relation_dashboard_uid.py" \
    --show-unit "tests/resources/show-unit/show-unit.yaml"

juju-doctor check \
    --probe "file://tests/resources/status" \
    --status "tests/resources/status/gagent-status.yaml"

juju-doctor check \
    --probe "github://canonical/grafana-agent-operator//probes" \
    --status "tests/resources/status/gagent-status.yaml" \
    --bundle "tests/resources/bundle/gagent-bundle.yaml"
```

## Development
```bash
git clone https://github.com/canonical/juju-doctor.git
python3 -m venv venv && source venv/bin/activate
pip install -e .
juju-doctor check --help
```
