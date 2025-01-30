## juju-doctor commands
```bash
juju-doctor check \
    --probe "file://tests/manual/status/gagent-vm-probe.py" \
    --status "tests/manual/status/gagent-vm-status.yaml"

juju-doctor check \
    --probe "file://tests/manual/bundle/gagent-vm-probe.py" \
    --bundle "tests/manual/bundle/gagent-vm-bundle.yaml"

juju-doctor check \
    --probe "file://tests/manual/show-unit/grafana-k8s-probe.py" \
    --show-unit "tests/manual/show-unit/cos-k8s-show-unit.yaml"
```