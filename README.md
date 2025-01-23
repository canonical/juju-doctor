# juju-doctor
> You deploy, we validate, you fix :)

## Features

### Probes
The probe only exists on the `feature/probes` branch in `grafana-k8s-operator`.  Run with:

```
juju show-unit grafana/0 | ./<path to grafana-k8s-operator>/probes/external/show-unit/relation_dashboard_uid.py
```

or

```
cat resources/show-unit.yaml | ./<path to grafana-k8s-operator>/probes/external/show-unit/relation_dashboard_uid.py
```

### Fetcher

Note: The fetcher is intended to work as a lib but currently has CLI functionality for prototyping.
1. `uv run python3 ./src/fetcher.py --probe https://raw.githubusercontent.com/canonical/grafana-k8s-operator/refs/heads/feature/probes/probes/external/show-unit/relation_dashboard_uid.py`
2. `uv run python3 ./src/fetcher.py --probes-dir grafana-k8s-operator --branch feature/probes`