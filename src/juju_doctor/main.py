"""Main Typer application to assemble the CLI."""

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Dict, List, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts, ModelArtifact
from juju_doctor.probes import Probe, ProbeResults

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

app = typer.Typer(pretty_exceptions_show_locals=False)
console = Console()
sys.setrecursionlimit(150)  # Protect against cirular RuleSet executions, increase if needed


@app.command()
def check(
    probe_urls: Annotated[
        List[str],
        typer.Option("--probe", "-p", help="URL of a probe containing probes to execute."),
    ] = [],
    models: Annotated[
        List[str],
        typer.Option("--model", "-m", help="Model on which to run live checks"),
    ] = [],
    status_files: Annotated[
        List[str],
        typer.Option("--status", help="Juju status in a .yaml format"),
    ] = [],
    bundle_files: Annotated[
        List[str],
        typer.Option("--bundle", help="Juju bundle in a .yaml format"),
    ] = [],
    show_unit_files: Annotated[
        List[str],
        typer.Option("--show-unit", help="Juju show-unit in a .yaml format"),
    ] = [],
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
    if models and any([status_files, bundle_files, show_unit_files]):
        raise Exception("If you pass a live model with --model, you cannot pass static files.")

    # Gather the input
    input: Dict[str, ModelArtifact] = {}
    if models:
        for model in models:
            model_artifact = ModelArtifact.from_live_model(model)
            input[model] = model_artifact
        artifacts = Artifacts(input)
    else:
        for f in status_files:
            input[f] = ModelArtifact.from_files(status_file=f)
        for f in bundle_files:
            input[f] = ModelArtifact.from_files(bundle_file=f)
        for f in show_unit_files:
            input[f] = ModelArtifact.from_files(show_unit_file=f)
        artifacts = Artifacts(input)

    # Gather the probes
    probes: List[Probe] = []
    with tempfile.TemporaryDirectory() as temp_folder:
        probes_folder = Path(temp_folder) / Path("probes")
        probes_folder.mkdir(parents=True)
        for probe_url in probe_urls:
            try:
                probes.extend(Probe.from_url(url=probe_url, probes_root=probes_folder))
            except RecursionError:
                log.error(
                    f"Recursion limit exceeded for probe: {probe_url}\n"
                    "Try reducing the intensity of probe chaining!"
                )

        # Run the probes
        probe_results: List[ProbeResults] = []
        for probe in probes:
            current_results: List[ProbeResults] = probe.run(artifacts)
            for r in current_results:
                if not format:
                    r.print(verbose=verbose)
            probe_results.extend(current_results)

    total_passed = len([pr for pr in probe_results if pr.passed])
    total_failed = len([pr for pr in probe_results if not pr.passed])
    match format:
        case "json":
            json_result = {"passed": total_passed, "failed": total_failed}
            console.print(json.dumps(json_result))
        case _:
            console.print(f"\nTotal: :green_circle: {total_passed} :red_circle: {total_failed}")


@app.command()
def help():
    """Show the help information for juju-doctor."""
    app().help()


if __name__ == "__main__":
    app()
