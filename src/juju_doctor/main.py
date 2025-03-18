"""Main Typer application to assemble the CLI."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Annotated, Dict, List, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts, ModelArtifact
from juju_doctor.fetcher import Fetcher, Probe

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


@app.command()
def check(
    probe_uris: Annotated[
        List[str],
        typer.Option("--probe", "-p", help="URI of a probe containing probes to execute."),
    ] = [],
    models: Annotated[
        List[str],
        typer.Option("--model", "-m", help="Model on which to run live checks"),
    ] = [],
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
    if models and any([status_file, bundle_file, show_unit_file]):
        raise Exception("If you pass a live model with --model, you cannot pass static files.")

    # Gather the input
    input: Dict[str, ModelArtifact] = {}
    if models:
        for model in models:
            model_artifact = ModelArtifact.from_live_model(model)
            input[model] = model_artifact
        artifacts = Artifacts(input)
    else:
        artifacts = Artifacts(
            {
                "(none)": ModelArtifact.from_files(
                    status_file=status_file,
                    bundle_file=bundle_file,
                    show_unit_file=show_unit_file,
                )
            }
        )

    # Gather the probes
    probes: List[Probe] = []
    with tempfile.TemporaryDirectory() as temp_folder:
        probes_folder = Path(temp_folder) / Path("probes")
        probes_folder.mkdir(parents=True)
        fetcher = Fetcher(probes_folder)
        for probe_uri in probe_uris:
            probes.extend(fetcher.fetch_probes(uri=probe_uri))

        # Run the probes
        total_passed = 0
        total_failed = 0

        for probe in probes:
            try:
                probe.run(artifacts)
                total_passed += 1
                _print(f":green_circle: {probe.name} succeeded", format=format)
            except Exception as e:
                total_failed += 1
                if verbose:
                    _print(f":red_circle: {probe.name} failed", format=format)
                    _print(f"[b]Exception[/b]: {e}", format=format)
                else:
                    _print(f":red_circle: {probe.name} failed ", format=format, end="")
                    _print(
                        f"({e}",
                        format=format,
                        overflow="ellipsis",
                        no_wrap=True,
                        width=40,
                        end="",
                    )
                    _print(")", format=format)

    json_result = {"passed": total_passed, "failed": total_failed}
    _print(f"\nTotal: :green_circle: {total_passed} :red_circle: {total_failed}", format=format)
    _print_formatted(json.dumps(json_result), format=format)


if __name__ == "__main__":
    app()
