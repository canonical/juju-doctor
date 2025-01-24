# juju-doctor
> You deploy, we validate, you fix :)

## Probes
Run a sample show-unit probe with:

```
juju show-unit grafana/0 | ./resources/relation_dashboard_uid.py
```

or

```
cat resources/show-unit.yaml | ./resources/relation_dashboard_uid.py
```

or

```
python src/main.py check --probe file://resources/show-unit --show-unit resources/show-unit.yaml
# If you want to see more internals, go to src/main.py and change the log level to INFO
```
