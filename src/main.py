"""Main Typer application to assemble the CLI."""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Annotated, List, Optional

import sh
import typer
from rich.console import Console
from rich.logging import RichHandler

from fetcher import Probe, fetch_probes

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

app = typer.Typer()
console = Console()


@app.command()
def check(
    # charms: Annotated[
    #     List[str],
    #     typer.Option("--charm", "-c", help="Name of a charm whose probes to execute"),
    # ] = [],
    probe_uris: Annotated[
        List[str],
        typer.Option("--probe", "-p", help="URI of a probe containing probes to execute." ""),
    ] = [],
    models: Annotated[
        List[str],
        typer.Option("--model", "-m", help="Model on which to run live checks"),
    ] = [],
    juju_status_file: Annotated[
        Optional[str],
        typer.Option("--status", help="Juju status in a .json format"),
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
                    if not juju_show_unit:
                        raise Exception("You didn't supply a juju show-unit.")
                    try:
                        sh.python(probe.path, _in=juju_show_unit)  # type: ignore
                        console.print(f"{probe.name} succeeded :tada:")
                    except sh.ErrorReturnCode:
                        console.print(f"{probe.name} failed :sob:")


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
