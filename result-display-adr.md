# Case study for different output representations when running
`-p "file://tests/resources/probes/python" -p "file://tests/resources/probes/ruleset/small-dir"`:
## Reduce the result functions into 1 probe
⭐️ This feels the most natural since it summarizes the result for each `--probe` arg or nested Ruleset probe
- Since the user needs to use the `--verbose` flag to check the specifics on Exceptions anyways, they can do this to understand the results of each function for that probe
- ❔ Should the `Total` summary include the number of failed assertions or probes?
- ❔ Should the function result summary be included in the parentheses () for the probe?
```
Results
├── fail
│   ├── 🔴 tests_resources_probes_python/failing.py (bundle, show_unit, status)
│   └── 🔴 tests_resources_probes_python_failing.py (bundle, show_unit, status)
└── pass
    ├── 🟢 tests_resources_probes_python/passing.py
    └── 🟢 tests_resources_probes_ruleset_small-dir/passing.py

Total: 🟢 6 🔴 6
```
## Full path with function names
❌ Visually hard to differentiate failing probe functions
```
Results
├── fail
│   ├── 🔴 tests_resources_probes_python/failing.py/bundle
│   ├── 🔴 tests_resources_probes_python/failing.py/show_unit
│   ├── 🔴 tests_resources_probes_python/failing.py/status
│   ├── 🔴 tests_resources_probes_python_failing.py/bundle
│   ├── 🔴 tests_resources_probes_python_failing.py/show_unit
│   └── 🔴 tests_resources_probes_python_failing.py/status
└── pass
    ├── 🟢 tests_resources_probes_python/passing.py/bundle
    ├── 🟢 tests_resources_probes_python/passing.py/show_unit
    ├── 🟢 tests_resources_probes_python/passing.py/status
    ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle
    ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit
    └── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status

Total: 🟢 6 🔴 6
```
## Grouped by parent with function names
❌ This is better than the last, but the output does not map 1-to-1 to the `--probe` args or Ruleset probes
```
Results
├── fail
│   ├── tests_resources_probes_python
│   │   ├── 🔴 failing.py/bundle
│   │   ├── 🔴 failing.py/show_unit
│   │   └── 🔴 failing.py/status
│   ├── 🔴 tests_resources_probes_python_failing.py/bundle
│   ├── 🔴 tests_resources_probes_python_failing.py/show_unit
│   └── 🔴 tests_resources_probes_python_failing.py/status
└── pass
    ├── tests_resources_probes_python
    │   ├── 🟢 passing.py/bundle
    │   ├── 🟢 passing.py/show_unit
    │   └── 🟢 passing.py/status
    ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/bundle
    ├── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/show_unit
    └── 🟢 tests_resources_probes_ruleset_small-dir/passing.py/status

Total: 🟢 6 🔴 6
```
## Grouped by (custom if supplied) ruleset name
❔ Group by `name` field for Ruleset probes

```yaml
name: Customer-A
probes:
    type: scriptlet
    url: file://tests/resources/probes/python/failing.py
  - name: Local ruleset
    type: ruleset
    url: file://tests/resources/probes/ruleset/small-dir  # could contain scriptlets or rulesets
  - name: Local probe
    type: scriptlet
    url: file://tests/resources/probes/python/passing.py
```
```yaml
name: Customer-B
probes:
  - name: Local probe
    type: scriptlet
    url: file://tests/resources/probes/python/failing.py
```

Given 2 ruleset files, the result could look like:

```
Results
├── Customer-A
│   ├── 🔴 tests_resources_probes_python_failing.py (bundle, show_unit, status)
│   ├── Local ruleset
│   │   ├── 🔴 tests_resources_probes_python_failing.py
│   │   └── 🟢 tests_resources_probes_ruleset_small-dir/passing.py
│   └── 🟢 Local probe
└── Customer-B
    └── 🔴 Local probe (bundle, show_unit, status)

Total: 🟢 6 🔴 9
```

- If a name key is not supplied then the default (fllattened) name will be used.
- Normally, we deduplicate probes but in this display format maybe we want to keep all duplicates for verbosity
    - For example, `Customer-A/tests_resources_probes_python_failing.py` and `Customer-B/Local probe` are duplicates according to the local filesystem although their names are different and may be used for multiple customer rulesets
- 