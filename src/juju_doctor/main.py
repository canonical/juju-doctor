"""Main Typer application to assemble the CLI."""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Dict, List, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts, ModelArtifact
from juju_doctor.probes import Probe
from juju_doctor.tree import OutputFormat, ProbeResultAggregator

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
        raise typer.BadParameter(
            "If you pass a live model with --model, you cannot pass static files."
        )

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
    builtins: List[dict] = []
    probes: List[Probe] = []
    with tempfile.TemporaryDirectory() as temp_folder:
        probes_folder = Path(temp_folder) / Path("probes")
        probes_folder.mkdir(parents=True)
        for probe_url in probe_urls:
            try:
                aggregation = Probe.from_url(url=probe_url, probes_root=probes_folder)
                probes.extend(aggregation.probes)
                # TODO It would be great if we could output the combined result from multiple probes to show the user what they created
                # E.g. 2 Rulesets: Applications: AM & Applications: Prom. Combined to be {"applications": ["AM", "Prom"]}
                builtins.append(aggregation.builtins)
            except RecursionError:
                log.error(
                    f"Recursion limit exceeded for probe: {probe_url}\n"
                    "Try reducing the intensity of probe chaining!"
                )

        probe_results = {}
        for builtin in builtins:
            for name, builtin_obj in builtin.items():
                # TODO Combine this with probe_results
                # TODO I think probe_results and builtin_results differ here because in probes we have Python as the lowest level which
                # Means probe.name -> [ProbeAggregationResults] makes sense. For the Builtins, we iterate through each one in main.py instead of appending to the list inside the .validate
                if builtin_obj.probe.name not in probe_results:
                    probe_results[builtin_obj.probe.name] = builtin_obj.validate(artifacts)
                else:
                    probe_results[builtin_obj.probe.name].extend(builtin_obj.validate(artifacts))

        for probe in probes:
            # Run the probes
            probe_results[probe.name] = probe.run(artifacts)

        output_fmt = OutputFormat(verbose, format)
        aggregator = ProbeResultAggregator(probe_results, output_fmt)
        aggregator.print_results()


@app.command()
def help():
    """Show the help information for juju-doctor."""
    app().help()


if __name__ == "__main__":
    app()
