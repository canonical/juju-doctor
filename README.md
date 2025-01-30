# juju-doctor
![PyPI](https://img.shields.io/pypi/v/juju-doctor)

You deploy, we validate, you fix it

## Probes
Run a sample show-unit probe with:

1. On a live model
`juju show-unit grafana/0 | ./my-probe.py`
2. On a file
`cat show-unit.yaml | ./my-probe.py`

Run that same probe with `juju-doctor`:
### On a live model
```
juju-doctor check \
    --probe "file://my-probe.py" \
    --model "grafana"
```
### On a file
```
juju-doctor check \
    --probe "file://my-probe.py" \
    --show-unit "show-unit.yaml"
```

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

## Development
```bash
git clone https://github.com/canonical/juju-doctor.git
python3 -m venv venv && source venv/bin/activate
pip install -e .
juju-doctor check --help
```
