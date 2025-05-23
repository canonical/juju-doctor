#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Helper module to fetch probes from local or remote endpoints."""

import logging
from enum import Enum
from pathlib import Path
from typing import List, Tuple
from urllib.error import URLError

import fsspec

log = logging.getLogger(__name__)


class FileExtensions(Enum):
    """Supported Probe file extensions."""

    PYTHON = {".py"}
    RULESET = {".yaml", ".yml"}

    @staticmethod
    def all():
        """Return all file extensions."""
        all = set()
        for f in FileExtensions:
            all = all | f.value
        return all


def parse_terraform_notation(url_without_scheme: str) -> Tuple[str, str, str]:
    """Extract the path from a GitHub URL in Terraform notation.

    Args:
        url_without_scheme: a Terraform-notation URL such as
            'canonical/juju-doctor//probes/path'

    Returns:
        org: The organization that ownes the repository, i.e. 'canonical'
        repo: The repository name, i.e. 'juju-doctor'
        path: The local path inside the specified repository,
            i.e. `probes/path`
    """
    try:
        # Extract the org and repository from the relative path
        org_and_repo, path = url_without_scheme.split("//")
        org, repo = org_and_repo.split("/")
    except ValueError:
        raise URLError(
            f"Invalid URL format: {url_without_scheme}. Use '//' to define 1 sub-directory "
            "and specify at most 1 branch."
        )
    return org, repo, path


def copy_probes(
    filesystem: fsspec.AbstractFileSystem, path: Path, probes_destination: Path
) -> List[Path]:
    """Scan a path for probes from a generic filesystem and copy them to a destination.

    If the same probe is specified multiple times, then the last instance of that probe overwrites
    the previous ones. Specifying duplicate probes is likely an accident by the user, but can occur
    with directories of probes or nesting of probes in Ruleset call paths.

    Args:
        filesystem: the abstraction of the filesystem containing the probe
        path: the path to the probe relative to the filesystem (either file or directory)
        probes_destination: the folder or file the probes are saved to

    Returns:
        A list of paths to the probes files copied over to 'probes_destination'
    """
    rpath, lpath = None, None
    # Copy the probes to the 'probes_destination' folder
    try:
        # If path ends with a "/", it will be assumed to be a directory
        # Can submit a list of paths, which may be glob-patterns and will be expanded.
        # https://github.com/fsspec/filesystem_spec/blob/master/docs/source/copying.rst
        rpath = f"{path.as_posix()}/" if path.is_dir() else path.as_posix()
        lpath = probes_destination.as_posix()
        if Path(lpath).exists():
            log.warning(f"Duplicate file detected: ./{rpath}, it will be skipped.")
        filesystem.get(rpath, lpath, recursive=True, auto_mkdir=True)
    except FileNotFoundError as e:
        log.warning(
            f"{e} file not found when attempting to copy "
            f"'{rpath}' to '{lpath}'"
        )

    # Create a Probe for each file in 'probes_destination' if it's a folder, else create just one
    if filesystem.isfile(rpath):
        probe_files: List[Path] = [probes_destination]
    else:
        probe_files: List[Path] = [
            f for f in probes_destination.rglob("*") if f.suffix.lower() in FileExtensions.all()
        ]
        log.info(f"copying {rpath} to {lpath} recursively")

    return probe_files
