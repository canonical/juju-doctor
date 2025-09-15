# How to contribute a Builtin plugin

Within a [RuleSet YAML file](../../README.md#ruleset), scriptlet probes are an escape hatch for complex, programmatic assertions. They are not intended to assert against common model patterns. For example, scriptlet probe authors may assert that certain applications or relations exist. This repetitiveness can be abstracted into Builtin assertions. Refer to this sample [RuleSet with Builtin assertions](../../tests/resources/probes/ruleset/builtins.yaml) as a starting point.

Builtins are probes, serving as complementary (or isolated) assertions, depending on the scope of their assertions.

```yaml
name: RuleSet - demo
probes:
  - name: Probe - test passing
    type: scriptlet
    url: file://tests/resources/probes/python/passing.py
  - name: My builtin
    type: builtin/my-builtin
    with:
      - foo: one
      - foo: two
```

## Builtin plugins

Juju-doctor is designed to accept builtin plugins via contributions made in the [src.juju_doctor.builtin](../../src/juju_doctor/builtin/) directory. Each of these files are a builtin and the name of the plugin is derived from the Python file name. Additionally, each builtin conforms to the [scriptlet interface](../../README.md#scriptlet):

```python
# src/juju_doctor/builtins/my-builtin.py
class FooModel(BaseModel):
    foo: str

def status(juju_statuses: Dict[str, Dict], **kwargs):
    assert kwargs["with_args"], "No arguments were provided"
    foo_models = [FooModel(**foo) for foo in kwargs["with_args"]]
    for foo_model in foo_models:
        # Run your assertion on each foo_model (FooModel) here ...
```

This would create the following API in a RuleSet:

```yaml
name: My builtin
  type: builtin/my-builtin
  with:
    - foo: one  # FooModel
    - foo: two  # FooModel
    # list more assertions here ...
```

Using [Pydantic's BaseModel](https://docs.pydantic.dev/latest/api/base_model/), you can control the schema of your builtin. For example, to improve on the `FooModel` from the previous example, we can forbid extra attributes to our builtin. 

```python
class FooModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    foo: str
```

This would create the following API in a RuleSet:

```yaml
name: My builtin
  type: builtin/my-builtin
  with:
    - foo: one
      invalid-key: this will raise a pydantic ValidationError
```

## How to test the plugin

To ensure that each builtin asserts correctly, its functional tests are defined in [doctest(s)](https://docs.python.org/3/library/doctest.html). Providing invalid user input and asserting that juju-doctor warns the user of mistakes, is a great way to ensure functionality of the builtin. To execute all the builtin probe doctests, run:
- `just doctest-builtin`.
