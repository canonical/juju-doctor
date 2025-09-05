from juju_doctor.main import app


def test_app_no_args_is_help():
    # GIVEN juju-doctor and its registered commands
    # WHEN no args are provided to the app and/or commands
    # THEN they show the help menu
    assert app.info.no_args_is_help is True
    for command in app.registered_commands:
        assert command.no_args_is_help is True
