# How to contribute a Builtin plugin

## Goal
Create a builtin plugin that juju-doctor can reference from a RuleSet. This guide shows where to place the code, which interface to implement, how to validate user input, and how to test your builtin.

Before you start
- Familiarity with Python and the repository layout.
- Basic knowledge of Pydantic for schema validation.
- The builtin files live under src/juju_doctor/builtin/ in the repository.

Quick example of using a builtin in a RuleSet:

```yaml
name: RuleSet - demo
probes:
  - type: scriptlet
    url: file://tests/resources/probes/python/passing.py
  - name: My builtin
    type: builtin/my-builtin
```

## What a builtin is
Builtins are reusable probes. They implement the same probe interface as scriptlets (for example, `status`, `bundle`, etc.), but they encapsulate common, repeatable assertions so RuleSets stay concise and maintainable.

## Where to put the code
Add a Python file to src/juju_doctor/builtin/. The filename determines the builtin name used in RuleSets. For example, a file named my-builtin.py is referenced as type: builtin/my-builtin.

## Implementing the interface
A builtin must implement one or more of the supported probe entry points (for example `status`, `bundle`). Each entry point receives probe artifacts and any extra options passed from the RuleSet as keyword arguments.

```python
# src/juju_doctor/builtins/my-builtin.py
def status(juju_statuses: Dict[str, Dict], **kwargs):
    foo_model = FooModel(**kwargs)
    for status_name, status in juju_statuses.items():
        # Run your assertion (FooModel) against all supplied status artifacts ...
        # NOTE: you can import any dependency that juju-doctor has access to
```

## Accepting multiple assertions in a RuleSet
To keep RuleSets readable, you can pass a list of argument sets under `with`. Each list item becomes the kwargs passed to the builtin function.

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

## Validating input with Pydantic
Use Pydantic models to validate and document the expected options for your builtin. This makes error messages clear and avoids raising internal errors when users pass invalid data.

```python
class FooModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    foo: str
    bar: str
```

This enforces the expected API and will raise a ValidationError for unexpected keys:

```yaml
name: My builtin
  type: builtin/my-builtin
  with:
    - foo: one
      bar: two
      invalid-key: raises a pydantic ValidationError
```

## How to add a builtin — step-by-step
1. Create a new file src/juju_doctor/builtin/my-builtin.py.
2. Implement the probe function(s) you need (e.g., `status`, `bundle`).
3. Recommended: Validate inputs with a Pydantic model to enforce an input schema for usability benefits.
4. Add doctests (see next section) to cover expected and invalid inputs.
5. Run the test suite and doctests.

## Testing your builtin
Write functional tests as Python doctests that exercise both valid and invalid usage. Doctests are a good place to assert that invalid input produces helpful messages for users.

To run all probe doctests:
- `just doctest`

## Tips

- Keep builtins focused and small — one purpose per builtin is easier to test and reuse.
- If you need an example to copy from, check the existing builtin plugins in src/juju_doctor/builtin/.