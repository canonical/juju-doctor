def test_probes_and_builtins_aggregation():
    assert False
    # GIVEN a Ruleset contains probes and some builtin assertions
    # WHEN the Ruleset executes
    # THEN the ResultAggregator (maybe remove the Probe in the name?) collects both


def test_builtins_in_tree():
    pass
    # GIVEN a Ruleset contains builtin assertions
    # WHEN the Ruleset executes
    # THEN the builtin assertions exist in the tree (in their own section
    # AND the number of pass/fail is correct
    # AND --verbose provides assertion information
    # AND the result can be piped to jq (maybe done in solution test)
