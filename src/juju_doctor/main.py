"""Main Typer application to assemble the CLI."""

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Set

import typer
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts, ModelArtifact
from juju_doctor.builtins import build_unified_schema
from juju_doctor.probes import Probe, ProbeTree
from juju_doctor.tree import OutputFormat, ProbeResultAggregator

# pyright: reportAttributeAccessIssue=false

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
log = logging.getLogger(__name__)

app = typer.Typer(pretty_exceptions_show_locals=False, no_args_is_help=True)
console = Console()
sys.setrecursionlimit(150)  # Protect against cirular RuleSet executions


@app.callback()
def callback():
    # When only 1 app.command exists, it is executed with `juju-doctor`, instead of the intended
    # help menu. app.callback overrides the CLI parameters for (without args) `juju-doctor`.
    """Collect, execute, and aggregate assertions against artifacts, representing a deployment."""


@app.command(no_args_is_help=True)
def check(
    ctx: typer.Context,
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
        str,
        typer.Option("--format", "-o", help="Specify output format."),
    ] = "",
):
    """Validate deployments, i.e. artifacts against assertions, i.e. probes.

    * Deployments can be (online) a live model or (offline) an artifact file.

    * Assertions can be sourced (local) from the current FS or (remote) from repositories.
    """
    # Input validation
    if models and any([status_files, bundle_files, show_unit_files]):
        raise typer.BadParameter("Live models (--model) and static files are mutually exclusive.")
    if not any([models, status_files, bundle_files, show_unit_files]):
        raise typer.BadParameter("No artifacts were specified, cannot validate the deployment.")
    if not probe_urls:
        raise typer.BadParameter("No probes were specified, cannot validate the deployment.")

    # Ensure valid JSON format in stdout
    # TODO Determine if this is desired, we basically hide warning when JSON output
    # makes tests harder to write. I.e. should a user clear warnings before getting
    # valid JSON -> this is the most important case!
    # TODO Another aspect to this issue is that the user can print within the probe and break JSON
    #      This might be user error though
    # TODO Maybe use it as a global with a wrapper method to print or not
    if format.lower() == "json":
        logging.disable(logging.ERROR)

    unique_probe_urls: Set[str] = set()
    for probe_url in probe_urls:
        if probe_url not in unique_probe_urls:
            unique_probe_urls.add(probe_url)
        else:
            log.warning(f"Duplicate probe arg detected: {probe_url}, it will be skipped.")

    provided_artifacts = {
        key.removesuffix("_files")
        for key, param in ctx.params.items()
        if key.endswith("_files") and param
    }

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
    probe_tree = ProbeTree()
    with tempfile.TemporaryDirectory() as temp_folder:
        probes_folder = Path(temp_folder) / Path("probes")
        probes_folder.mkdir(parents=True)
        for probe_url in unique_probe_urls:
            try:
                probe_tree = Probe.from_url(probe_url, probes_folder, probe_tree=probe_tree)
            except RecursionError:
                log.error(
                    f"Recursion limit exceeded for probe: {probe_url}\n"
                    "Try reducing the intensity of probe chaining!"
                )

        check_functions: Set[str] = set()

        # Probes
        for probe in probe_tree.probes:
            check_functions |= set(probe.get_functions().keys())
            probe.run(artifacts)

        # Builtins
        for _type, builtin in probe_tree.builtins.items():
            for ruleset_id, builtin_obj in builtin.items():
                # TODO: With RuleSetModel, we can stop schema validating in validate_assertions
                #       and only do it when we find a RuleSet in aggregation or from_url
                assertion_results = builtin_obj.schema.validate_assertions(builtin_obj, artifacts)
                if _type == "probes":
                    # Probes results are already determined in probe.run
                    continue
                check_functions.add(builtin_obj.artifact_type)
                probe = Probe(
                    Path(f"builtins:{_type}"),
                    Path(),
                    probes_chain=ruleset_id,
                    results=assertion_results,
                )
                probe_tree.probes.append(probe)

        if not provided_artifacts.issubset(check_functions):
            useless_artifacts = ", ".join(provided_artifacts - check_functions)
            log.warning(
                f"The '{useless_artifacts}' artifact was provided, but not used by any probes "
                "or builtin assertions."
            )

        if probe_tree.tree:
            output_fmt = OutputFormat(verbose, format)
            aggregator = ProbeResultAggregator(probe_tree.probes, output_fmt, probe_tree.tree)
            aggregator.print_results()

# TODO: Remove if not needed
@app.command(no_args_is_help=True)
def schema(
    stdout: Annotated[
        bool,
        typer.Option("--stdout", help="Output the schema to stdout."),
    ] = False,
    file: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Specify the file's relative destination path."),
    ] = None,
):
    """Generate and output the unified schema."""
    schema = build_unified_schema()  # Dict

    if file:
        output_path = Path(file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the schema to the specified file
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)

        console.print(f"Schema saved to {output_path}")

    if stdout:
        console.print(schema)


if __name__ == "__main__":
    app()
