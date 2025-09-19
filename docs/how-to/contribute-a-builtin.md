# How to contribute a Builtin plugin

Within a [RuleSet YAML file](../../README.md#ruleset), scriptlet probes are an escape hatch for complex, programmatic assertions. They are not intended to assert against common model patterns. For example, scriptlet probe authors may assert that certain applications or relations exist. This repetitiveness can be abstracted into Builtin assertions. Refer to this sample [RuleSet with Builtin assertions](../../tests/resources/probes/ruleset/builtins.yaml) as a starting point.

Builtins are probes, serving as complementary (or isolated) assertions, depending on the scope of their assertions.

```yaml
name: RuleSet - demo
probes:
  - type: scriptlet
    url: file://tests/resources/probes/python/passing.py
  - name: My builtin
    type: builtin/my-builtin
```

## Builtin plugins

Juju-doctor is designed to accept builtin plugins via contributions made in the [src.juju_doctor.builtin](../../src/juju_doctor/builtin/) directory. Each of these files are a builtin and the name of the plugin is derived from the Python file name. Additionally, each builtin Python file conforms to the [scriptlet interface](../../README.md#scriptlet), i.e. it must define, at least one of, the supported functions (e.g., `status`, `bundle`, etc.):

```python
# src/juju_doctor/builtins/my-builtin.py
def status(juju_statuses: Dict[str, Dict], **kwargs):
    foo_model = FooModel(**kwargs)
    for status_name, status in juju_statuses.items():
        # Run your assertion (FooModel) against all supplied status artifacts ...
        # NOTE: you can import any dependency that juju-doctor has access to
```

This would allow you to use it in a RuleSet:

```yaml
name: My builtin
  type: builtin/my-builtin
  with:
    - foo: one
      bar: two
    - foo: three
      bar: four
    # list more assertions here ...
```
Any arguments under `with` will be passed to the `status` function, accessed via `**kwargs`. In favor of readability, we can list multiple assertions nested under `with` to avoid duplicate `type` definitions.

Using [Pydantic's BaseModel](https://docs.pydantic.dev/latest/api/base_model/), you can control the schema of the builtin. For example, creating a `FooModel` can forbid extra attributes to the builtin.

```python
class FooModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    foo: str
    bar: str
```

This would enforce the following API in a RuleSet:

```yaml
name: My builtin
  type: builtin/my-builtin
  with:
    - foo: one
      bar: two
      invalid-key: raises a pydantic ValidationError
```

## How to test the plugin

To ensure that each builtin asserts correctly, its functional tests are defined in [doctest(s)](https://docs.python.org/3/library/doctest.html). Providing invalid user input and asserting that juju-doctor warns the user of mistakes, is a great way to ensure functionality of the builtin. Check out one of the existing plugins in the [src.juju_doctor.builtin](../../src/juju_doctor/builtin/) directory as an example. To execute all the probe doctests, run:
- `just doctest`
