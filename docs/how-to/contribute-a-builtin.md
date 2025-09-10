# How to contribute a Builtin plugin

Within a [RuleSet YAML file](../../README.md#ruleset), scriptlet probes are an escape hatch for complex, programmatic assertions. They are not intended to assert against common model patterns. For example, scriptlet probe authors may assert that certain applications or relations exist. This repetitiveness can be abstracted into Builtin assertions. Refer to this sample [RuleSet with Builtin assertions](../../tests/resources/probes/ruleset/builtins.yaml) as a starting point.

In this RuleSet we can see that builtins and probes can both be defined, serving as complementary (or isolated) assertions, depending on the scope of their assertions. 

```yaml
name: RuleSet - demo
builtins:
  my-builtin:
    - useful-key: value to assert against
probes:
  - name: Probe - test passing
    type: scriptlet
    url: file://tests/resources/probes/python/passing.py
```

## Builtin plugins

Juju-doctor is designed to accept builtin plugins via contributions made in the [src.juju_doctor.builtins](../../src/juju_doctor/builtins/) directory. Each of these files are a builtin and the name of the plugin is derived from the file name. Additionally, each builtin conforms to the following interface:

```python
# src/juju_doctor/builtins/my-builtin.py
class CustomModel(BaseModel):
    foo: bool

class ValidBuiltin(BaseBuiltin):
    assertions: List[CustomModel]

    def validate_assertions(self, artifacts: Artifacts) -> List[AssertionResult]:
        pass
```

This would create the following API in a RuleSet:

```yaml
name: RuleSet - containing my newly authored builtin
builtins:
  my-builtin:
    - foo: true
```

Using [Pydantic's BaseModel](https://docs.pydantic.dev/latest/api/base_model/), you can control the schema of your builtin. For example, to improve on the `CustomModel` from the previous example, we can forbid extra attributes to our builtin. 

```python
class CustomModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    foo: bool
```

This would create the following API in a RuleSet:

```yaml
name: RuleSet - containing my newly authored builtin
builtins:
  my-builtin:
    - foo: true
      invalid-key: this will raise a pydantic ValidationError
```

## How to test the plugin

Juju-doctor has [unit tests](../../tests/unit/builtins/) for basic builtin functionality, e.g. validating the interface of each plugin, so the minimum steps are covered. To ensure that each builtin asserts correctly, its functional tests should be added to [solution tests](../../tests/solution/check_command/builtins/). Providing basic invalid RuleSet builtins and asserting that juju-doctor warns the user of mistakes, is a great way to ensure functionality of the builtin.