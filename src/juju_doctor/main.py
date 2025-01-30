"""Main Typer application to assemble the CLI."""

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import sh
import typer
import yaml
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.fetcher import Probe, ProbeCategory, fetch_probes

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

app = typer.Typer()
console = Console()


def _print(message: str, format: Optional[str], *args, **kwargs):
    """Print a message based on the output format."""
    if not format:
        console.print(message, *args, **kwargs)

def _print_formatted(message, format: Optional[str], *args, **kwargs):
    """Print a formatted message based on the output format."""
    if format:
        match format.lower():
            case "json":
                console.print(message, end="", *args, **kwargs)
            case _:
                raise NotImplementedError


def _read_file(filename: Optional[str]) -> Optional[str]:
    """Read a file into a string."""
    if not filename:
        return None
    with open(filename, "r") as f:
        contents = f.read()
        # Parse all YAML documents and return only the first one
        # https://github.com/canonical/juju-doctor/issues/10
        return list(yaml.safe_load_all(contents))[0]


def _get_model_data(model: str, probe_category: ProbeCategory) -> str:
    """Get data from a live model according to the type of probe."""
    match probe_category:
        case ProbeCategory.STATUS:
            return sh.juju.status(model=model, format="yaml", _tty_out=False)
        case ProbeCategory.BUNDLE:
            return sh.juju("export-bundle", model=model, _tty_out=False)
        case ProbeCategory.SHOW_UNIT:
            units: List[str] = []
            show_units: Dict[str, Any] = {}  # List of show-unit results in dictionary form
            juju_status = yaml.safe_load(sh.juju.status(model=model, format="yaml", _tty_out=False))
            for app in juju_status["applications"]:
                # Subordinate charms don't have a "units" key, so the parsing is different
                app_status = juju_status["applications"][app]
                if "units" in app_status:  # if the app is not a subordinate
                    units.extend(app_status["units"].keys())
                    # Check for subordinates to each unit
                    for unit in app_status["units"].keys():
                        unit_status = app_status["units"][unit]
                        if "subordinates" in unit_status:
                            units.extend(unit_status["subordinates"].keys())
            for unit in units:
                show_unit = yaml.safe_load(
                    sh.juju("show-unit", unit, model=model, format="yaml", _tty_out=False)
                )
                show_units.update(show_unit)
            return yaml.dump(show_units)


@app.command()
def check(
    probe_uris: Annotated[
        List[str],
        typer.Option("--probe", "-p", help="URI of a probe containing probes to execute."),
    ] = [],
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Model on which to run live checks"),
    ] = None,
    status_file: Annotated[
        Optional[str],
        typer.Option("--status", help="Juju status in a .yaml format"),
    ] = None,
    bundle_file: Annotated[
        Optional[str],
        typer.Option("--bundle", help="Juju bundle in a .yaml format"),
    ] = None,
    show_unit_file: Annotated[
        Optional[str],
        typer.Option("--show-unit", help="Juju show-unit in a .yaml format"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
    format: Annotated[
        Optional[str],
        typer.Option("--format", "-o", help="Specify output format."),
    ] = None,
):
    """Run checks on a certain model."""
    # Input validation
    if model and any([status_file, bundle_file, show_unit_file]):
        raise Exception("If you pass a live model with --model, you cannot pass static files.")

    # Run the actual checks
    with tempfile.TemporaryDirectory() as temp_folder:
        json_result = {}
        probes_folder = Path(temp_folder) / Path("probes")
        probes_folder.mkdir(parents=True)
        log.info(f"Created temporary folder: {temp_folder}")

        input_data: Dict[str, Optional[str]] = {}
        if model:
            log.info(f"Getting input data from model {model}")
            for category in ProbeCategory:
                input_data[category.value] = _get_model_data(model=model, probe_category=category)
        else:
            log.info(f"Getting input data from files: {status_file} {bundle_file} {show_unit_file}")
            input_data[ProbeCategory.STATUS.value] = _read_file(status_file) or None
            input_data[ProbeCategory.BUNDLE.value] = _read_file(bundle_file) or None
            input_data[ProbeCategory.SHOW_UNIT.value] = _read_file(show_unit_file) or None

        total_succeeded = 0
        total_failed = 0
        probes: List[Probe] = []
        for probe_uri in probe_uris:
            probes.extend(fetch_probes(uri=probe_uri, destination=probes_folder))

        # Run one category of probes at a time
        for category in ProbeCategory:
            _print(f"[b]Probe type: {category.value}[/b]", format=format)
            for probe in probes:
                if not probe.is_category(category):
                    continue
                log.info(f"Running probe {probe}")
                probe_input = input_data[category.value]
                if not probe_input:
                    raise Exception(f"You didn't supply {category.value} input or a live model.")
                try:
                    sh.python(probe.local_path, _in=probe_input)
                    _print(f":green_circle: {probe.name} succeeded", format=format)
                    total_succeeded += 1
                except sh.ErrorReturnCode as error:
                    total_failed += 1
                    # TODO: in verbose mode, print all the things:
                    # .full_cmd, .stdout, .stderr, .exit_code
                    if verbose:
                        _print(f":red_circle: {probe.name} failed", format=format)
                        _print(f"[b]Exit code[/b]: {error.exit_code}", format=format)
                        _print(f"[b]STDOUT[/b]\n{error.stdout.decode()}", format=format)
                        _print(f"[b]STDERR[/b]\n{error.stderr.decode()}", format=format)
                    else:
                        cmd_error = error.stderr.decode().replace("\n", " ")
                        _print(f":red_circle: {probe.name} failed ", format=format, end="")
                        _print(
                            f"({cmd_error}",
                            format=format,
                            overflow="ellipsis",
                            no_wrap=True,
                            width=40,
                            end="",
                        )
                        _print(")", format=format)

    json_result.update({"passed": total_succeeded, "failed": total_failed})

    _print(f"\nTotal: :green_circle: {total_succeeded} :red_circle: {total_failed}", format=format)
    _print_formatted(json.dumps(json_result), format=format)


@app.command()
def hello(name: str):
    """Test command to say hello."""
    console.print(f"Hello {name}!")


if __name__ == "__main__":
    if sys.stdin.isatty():
        # No piped input, read from user input interactively
        app()
    else:
        # Piped input, process it
        input_data = sys.stdin.read()
        print("Received input:")
        print(input_data)
