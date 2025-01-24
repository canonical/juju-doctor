"""Main Typer application to assemble the CLI."""

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

from fetcher import Probe, fetch_probes

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

app = typer.Typer()
console = Console()


def _read_file(filename: str):
    """Read a file into a string."""
    with open(filename, "r") as f:
        return f.read()


def _get_model_data(model: str, probe_category: str) -> str:
    """Get data from a live model according to the type of probe."""
    match probe_category:
        case "status":
            return sh.juju.status(model=model, format="yaml", _tty_out=False)
        case "bundle":
            return sh.juju("export-bundle", model=model, format="yaml", _tty_out=False)
        case "show-unit":
            units: List[str] = []
            show_units: Dict[str, Any] = {}  # List of show-unit results in dictionary form
            juju_status = yaml.safe_load(
                sh.juju.status(model=model, format="yaml", _tty_out=False)
            )
            for app in juju_status["applications"]:
                units.extend(juju_status["applications"][app]["units"].keys())
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
        typer.Option("--probe", "-p", help="URI of a probe containing probes to execute." ""),
    ] = [],
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Model on which to run live checks"),
    ] = None,
    juju_status_file: Annotated[
        Optional[str],
        typer.Option("--status", help="Juju status in a .yaml format"),
    ] = None,
    juju_bundle_file: Annotated[
        Optional[str],
        typer.Option("--bundle", help="Juju bundle in a .yaml format"),
    ] = None,
    juju_show_unit_file: Annotated[
        Optional[str],
        typer.Option("--show-unit", help="Juju show-unit in a .yaml format"),
    ] = None,
):
    """Run checks on a certain model."""
    with tempfile.TemporaryDirectory() as temp_folder:
        probes_show_unit_path = Path(f"{temp_folder}/probes/show-unit")
        probes_show_unit_path.mkdir(parents=True)
        log.info(f"Created temporary folder: {temp_folder}")

        juju_show_unit = None
        if juju_show_unit_file:
            with open(juju_show_unit_file, "r") as f:
                juju_show_unit = f.read()

        for probe_uri in probe_uris:
            probes: List[Probe] = fetch_probes(uri=probe_uri, destination=probes_show_unit_path)

            for probe in probes:
                log.info(f"Running probe {probe}")
                if probe.is_show_unit():
                    input_data = juju_show_unit
                    if model and not input_data:
                        input_data = _get_model_data(model, "show-unit")
                    if not input_data:
                        raise Exception("You didn't supply a juju show-unit or a live model.")
                    try:
                        sh.python(probe.path, _in=input_data)
                        console.print(f":green_circle: {probe.name} succeeded")
                    except sh.ErrorReturnCode:
                        console.print(f":red_circle: {probe.name} failed")


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
