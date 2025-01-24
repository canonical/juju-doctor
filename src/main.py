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

from fetcher import Probe, ProbeCategory, fetch_probes

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

app = typer.Typer()
console = Console()


def _read_file(filename: Optional[str]) -> Optional[str]:
    """Read a file into a string."""
    if not filename:
        return None
    with open(filename, "r") as f:
        return f.read()


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
):
    """Run checks on a certain model."""
    # Input validation
    if model and any([status_file, bundle_file, show_unit_file]):
        raise Exception("If you pass a live model with --model, you cannot pass static files.")

    # Run the actual checks
    with tempfile.TemporaryDirectory() as temp_folder:
        probes_folder = Path(temp_folder) / Path("probes")
        probes_folder.mkdir(parents=True)
        log.info(f"Created temporary folder: {temp_folder}")

        input_data: Dict[str, Optional[str]] = {}
        if model:
            log.info(f"Getting input data from model {model}")
            for category in ProbeCategory:
                input_data[category.value] = _get_model_data(model=model, probe_category=category)
        else:
            log.info(
                f"Getting input data from files: {status_file} {bundle_file} {show_unit_file}"
            )
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
            console.print(f"Probe type: {category.value}", style="bold")
            for probe in probes:
                if not probe.is_category(category):
                    continue
                log.info(f"Running probe {probe}")
                probe_input = input_data[category.value]
                if not probe_input:
                    raise Exception("You didn't supply a juju show-unit or a live model.")
                try:
                    # Strip /probes from end of probes_folder
                    strip_probes_from_path = Path(*[part for part in probes_folder.parts if part != "probes"])
                    # Strip branch from end of path
                    if "@" in probe.path.name:
                        path, branch = probe.path.name.split("@")
                    sh.python(strip_probes_from_path / path, _in=probe_input)
                    console.print(f":green_circle: {probe.name} succeeded")
                    total_succeeded += 1
                except sh.ErrorReturnCode_1:
                    console.print(f":red_circle: {probe.name} failed")
                    total_failed += 1

        console.print(f"\nTotal: :green_circle: {total_succeeded} :red_circle: {total_failed}")


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
