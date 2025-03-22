#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Helper module to fetch probes from local or remote endpoints."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from juju_doctor.probes import Probe, ProbeFS, probe_name_as_posix

log = logging.getLogger(__name__)


class CircularRulesetError(Exception):
    """Raised when a Ruleset execution chain exceeds 2 Rulesets."""


def _read_file(filename: Path) -> Optional[Dict]:
    """Read a file into a string."""
    try:
        with open(str(filename), "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log.warning(f"Error: File '{filename}' not found.")
    except yaml.YAMLError as e:
        log.warning(f"Error: Failed to parse YAML in '{filename}': {e}")
    except Exception as e:
        log.warning(f"Unexpected error while reading '{filename}': {e}")
    return None

class RuleSet:
    """Represents a set of probes defined in a ruleset configuration file.

    Supports recursive aggregation of probes, handling scriptlets and nested rulesets.
    Detects and prevents circular dependencies.
    """

    extensions: List[str] = [".yaml", ".yml"]

    def __init__(self, name: str, destination: Path, probe_path: Path):
        """Initialize a RuleSet instance.

        Args:
            name (str): The name of the ruleset.
            destination (Path): The directory where probes are stored.
            probe_path (Path): The relative path to the ruleset configuration file.
        """
        self.name = name
        self.destination = destination
        self.probe_path = probe_path
        self.probes = []

    def aggregate_probes(self) -> List:
        """Obtain all the probes from the RuleSet.

        This method is recursive when it finds another RuleSet probe.

        Raises CircularRulesetError if a Ruleset execution chain contained more than 2 Rulesets.
        """
        content = _read_file(self.probe_path)
        if not content:
            return []
        ruleset_probes = content.get("probes", [])
        probes = []
        for probe in ruleset_probes:
            match probe["type"]:
                case "scriptlet":
                    probes.extend(Fetcher.fetch_probes(self.destination, probe["uri"]))
                case "ruleset":
                    if self._is_circular_ruleset(self.destination, probe["uri"]):
                        raise CircularRulesetError("A Ruleset execution chain contained more than 2 Rulesets")
                    probe_fs = ProbeFS(self.destination, probe["uri"])
                    name = probe_name_as_posix(self.destination, probe_fs.local_path)
                    ruleset = RuleSet(name, self.destination, probe_fs.rel_path)
                    # Recurses until we no longer have Ruleset probes
                    nested_ruleset_probes = ruleset.aggregate_probes()
                    log.info(f"Fetched probes: {ruleset.probes}")
                    probes.extend(nested_ruleset_probes)
                case _:
                    # TODO "built-in" directives, e.g. "apps/has-relation" or "apps/has-subordinate"
                    pass

        return probes

    @staticmethod
    def _is_circular_ruleset(destination: Path, uri: str) -> bool:
        probe_fs = ProbeFS(destination, uri)
        # Get the neseted RuleSet to determine the probe list
        ruleset = RuleSet("test-circular", destination, probe_fs.rel_path)
        content = _read_file(ruleset.probe_path)
        if not content:
            return False
        ruleset_probes = content.get("probes", [])
        return any(probe["type"] == "ruleset" for probe in ruleset_probes)


class Fetcher(object):
    """A fetcher which uses protocols for obtaining a remote FS to copy to a local one."""

    @staticmethod
    def _copy_remote_to_local(probe_fs: ProbeFS):
        try:
            # If path ends with a "/", it will be assumed to be a directory
            # Can submit a list of paths, which may be glob-patterns and will be expanded.
            # https://github.com/fsspec/filesystem_spec/blob/master/docs/source/copying.rst
            probe_fs.filesystem.get(
                probe_fs.rel_path.as_posix(), probe_fs.local_path.as_posix(), recursive=True, auto_mkdir=True
            )
        except FileNotFoundError as e:
            log.warning(
                f"{e} file not found when attempting to copy "
                f"'{probe_fs.rel_path.as_posix()}' to '{probe_fs.local_path.as_posix()}'"
            )
            raise

    @staticmethod
    def _build_probes(probe_fs: ProbeFS) -> List[Probe]:
        if probe_fs.filesystem.isfile(probe_fs.rel_path.as_posix()):
            probe_files = [probe_fs.local_path]
        else:
            probe_files: List[Path] = [
                f for f in probe_fs.local_path.rglob("*") if f.suffix.lower() in [".py"] + RuleSet.extensions
            ]
        probes = []
        for probe_path in probe_files:
            name = probe_name_as_posix(probe_fs.destination, probe_path)
            if probe_path.suffix.lower() in RuleSet.extensions:
                ruleset = RuleSet(name, probe_fs.destination, probe_path)
                ruleset_probes = ruleset.aggregate_probes()
                log.info(f"Fetched probes: {ruleset.probes}")
                probes.extend(ruleset_probes)
            else:
                probe = Probe(
                    name=name,
                    uri=probe_fs.uri,
                    original_path=probe_fs.rel_path,
                    path=probe_path,
                )
                log.info(f"Fetched probe: {probe}")
                probes.append(probe)

        return probes

    @staticmethod
    def fetch_probes(destination: Path, uri: str) -> List[Probe]:
        """Fetch probes from a source to a local directory.

        Args:
            destination (Path): the file path for the probes on the local FS.
            uri (str): a URI to a probe living somewhere.
                Currently only supports:
                - 'github://' with Terraform notation
                - 'file://'
        """
        probe_fs = ProbeFS(destination, uri)
        try:
            Fetcher._copy_remote_to_local(probe_fs)
        except FileNotFoundError:
            pass

        log.info(f"copying {probe_fs.rel_path.as_posix()} to {probe_fs.local_path.as_posix()} recursively")

        return Fetcher._build_probes(probe_fs)
