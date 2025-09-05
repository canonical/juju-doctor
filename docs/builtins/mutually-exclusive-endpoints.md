TODO: Determine if these are necessary once builtins are in separate files

## Description
Any app of type grafana-agent should not be related to both ...

applicable for: status

## Examples
```yaml
mutually-exclusive-endpoints:
  charm-name: grafana-agent
  interfaces:
    - juju-info
    - cos_agent
```

```python
def mutually_exl_endpts(status, **kwargs):

```