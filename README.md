# juju-doctor
> You deploy, we validate, you fix :)

## Features

### Probes
Run a sample show-unit probe with:

```
juju show-unit grafana/0 | ./resources/relation_dashboard_uid.py
```

or

```
cat resources/show-unit.yaml | ./resources/relation_dashboard_uid.py
```

### Fetcher

Note: The fetcher is intended to work as a lib but currently takes args for prototyping.
```
uv run python3 ./src/fetcher.py ./resources
uv run python3 ./src/fetcher.py ./resources/relation_dashboard_uid.py
uv run python3 ./src/fetcher.py "https://raw.githubusercontent.com/canonical/grafana-k8s-operator//probes/external/show-unit/relation_dashboard_uid.py?ref=feature/probes"
uv run python3 ./src/fetcher.py "https://raw.githubusercontent.com/canonical/grafana-k8s-operator//probes/external/show-unit?ref=feature/probes"
```