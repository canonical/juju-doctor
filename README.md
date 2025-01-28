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
    --probe "file://resources/show-unit/relation_dashboard_uid.py" \
    --model "grafana"
```
2. On a file
```
juju-doctor check \
    --probe "file://resources/show-unit/relation_dashboard_uid.py" \
    --show-unit "resources/show-unit/show-unit.yaml"
```
> If you want to see more internals, go to src/main.py and change the log level to INFO


## Demo juju-doctor commands
```
juju-doctor check \
    --probe "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py" \
    --model "cos"

juju-doctor check \
    --probe "file://resources/show-unit/relation_dashboard_uid.py" \
    --show-unit "resources/show-unit/show-unit.yaml"

juju-doctor check \
    --probe "file://resources/status" \
    --status "resources/status/gagent-status.yaml"

juju-doctor check \
    --probe "github://canonical/grafana-k8s-operator//probes/show-unit/relation_dashboard_uid.py" \
    --show-unit "resources/show-unit/show-unit.yaml"

juju-doctor check \
    --probe "github://canonical/grafana-agent-operator//probes" \
    --status "resources/status/gagent-status.yaml" \
    --bundle "resources/bundle/gagent-bundle.yaml"
```

## Development
```bash
git clone https://github.com/MichaelThamm/juju-doctor.git
python3 -m venv venv && source venv/bin/activate
pip install -e juju-doctor
juju-doctor check --help
```
