def test_unknown_top_level_keys():
    pass
    # TODO Consider using inline YAML for tests to not pollute the tests/resources
    # GIVEN a Ruleset with unknown top-level keys
    # WHEN the Ruleset executes the builtin assertions
    # THEN the unknown top-level keys are ignored

def test_nested_builtins():
    pass
    # GIVEN a Ruleset executes other Rulesets
    # WHEN the executed Ruleset has builtin assertions
    # THEN they are aggregated with the others builtin assertions
