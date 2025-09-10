def status(juju_statuses, **kwargs):
    raise Exception("I'm the status probe, and I failed")


def bundle(juju_bundles, **kwargs):
    raise Exception("Bundle probe here, something went wrong")


def show_unit(juju_show_units, **kwargs):
    raise Exception("I'm the show-unit probe, bad things happened")
