"""Main Typer application to assemble the CLI."""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Dict, List, Set

import typer
import yaml
from pydantic.json_schema import models_json_schema
from rich.console import Console
from rich.logging import RichHandler

from juju_doctor.artifacts import Artifacts, ModelArtifact
from juju_doctor.constants import BUILTIN_DIR
from juju_doctor.fetcher import find_pydantic_models_in_module, import_module_from_path
from juju_doctor.probes import Probe, ProbeTree, RuleSetModel
from juju_doctor.results import CheckFormat, SchemaType
from juju_doctor.tree import FormatTracker, ResultAggregator

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
    format_type: Annotated[
        CheckFormat,
        typer.Option("--format", "-o", help="Specify output format.", case_sensitive=False),
    ] = CheckFormat.tree,
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
    if format_type and format_type.lower() == CheckFormat.json.value:
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

        # Probes
        check_functions: Set[str] = set()
        for probe in probe_tree.probes:
            check_functions |= set(probe.get_functions().keys())
            if probe.probe_definition and probe.probe_definition.with_:
                for with_ in probe.probe_definition.with_:
                    probe.run(artifacts, **with_)
            else:
                probe.run(artifacts)

        probe_tree.summarize_results()

        if not provided_artifacts.issubset(check_functions):
            useless_artifacts = ", ".join(provided_artifacts - check_functions)
            log.warning(
                f'The "{useless_artifacts}" artifact was provided, but not used by any probes '
                "or builtin assertions."
            )

        if probe_tree.tree:
            fmt = FormatTracker(verbose, format_type)
            aggregator = ResultAggregator(probe_tree.probes, fmt, probe_tree.tree)
            aggregator.print_results()


@app.command(no_args_is_help=True)
def schema(
    schema_type: Annotated[
        SchemaType,
        typer.Option(
            "--type", "-t", help="Specify which schema type to output.", case_sensitive=False
        ),
    ] = SchemaType.ruleset,
):
    """Generate and output the schema."""
    if schema_type == SchemaType.ruleset.value:
        schema = RuleSetModel.model_json_schema()
    elif schema_type == SchemaType.builtins.value:
        root = Path(BUILTIN_DIR)
        models = []
        for path in sorted(root.glob("*.py")):
            try:
                mod = import_module_from_path(path)
            except Exception as e:
                log.error(f"Error importing module ({path.name}): {e}")
                continue
            for cls in find_pydantic_models_in_module(mod):
                try:
                    models.append(cls)
                except Exception as e:
                    log.error(f"Error in file ({path.name}:{cls.__name__}): {e}")
        _, schema = models_json_schema(
            [(model, "validation") for model in models],
        )
    else:
        raise NotImplementedError

    console.print(yaml.dump(schema, indent=2), no_wrap=True)


if __name__ == "__main__":
    app()
