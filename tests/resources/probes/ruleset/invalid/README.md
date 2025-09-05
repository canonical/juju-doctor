All RuleSet YAML files in this "invalid" directory will fail when executed by Juju-doctor. The means for failure can vary, e.g. pydantic.ValidationError, an assertion failed, etc.

If a file raises a pydantic.ValidationError, prefix the file name with "raises-" for correct handling in solution tests.