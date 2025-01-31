#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Helper module to fetch probes from local or remote endpoints."""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional
from urllib.error import URLError
from urllib.parse import ParseResult, urlparse

import fsspec

log = logging.getLogger(__name__)


class ProbeCategory(Enum):
    """Different categories of probes."""

    STATUS = "status"
    BUNDLE = "bundle"
    SHOW_UNIT = "show-unit"


@dataclass
class Probe:
    """A probe that can be executed via juju-doctor."""

    name: str
    category: Optional[ProbeCategory]
    uri: str
    original_path: Path
    local_path: Path

    def is_category(self, category: ProbeCategory) -> bool:
        """Check if the Probe belongs to the specified category."""
        return self.category == category


def _get_filesystem(filesystem: fsspec.filesystem, path: Path, local_path: Path, parsed_uri: ParseResult):
    try:
        # If path ends with a "/", it will be assumed to be a directory
        # Can submit a list of paths, which may be glob-patterns and will be expanded.
        # https://github.com/fsspec/filesystem_spec/blob/master/docs/source/copying.rst
        filesystem.get(path.as_posix(), local_path.as_posix(), recursive=True, auto_mkdir=True)
    except FileNotFoundError as e:
        log.warn(f"file not found when attempting to copy {path.as_posix()} to {local_path.as_posix()}: {e}")
        raise

# TODO turn this into a class
def fetch_probes(uri: str, destination: Path) -> List[Probe]:
    """Fetch probes from a source to a local directory.

    Args:
        uri: a URI to a probe living somewhere.
            Currently only supports:
            - 'github://' with Terraform notation
            - 'file://'
            - 'charm://' for fetching from charm(-k8s)-operator remotes
        destination: the folder where to save the probes.
    """
    probes = []
    parsed_uri = urlparse(uri)
    probe_path = parsed_uri.netloc + parsed_uri.path
    subfolder = probe_path.replace("/", "_")
    local_path = destination / subfolder
    # Extract the branch name if present
    if parsed_uri.query:
        branch = parsed_uri.query
    else:
        branch = "main"

    match parsed_uri.scheme:
        case "file":
            path = Path(probe_path)
            filesystem = fsspec.filesystem(protocol="file")
        case "github":
            try:
                # Extract the org and repository from the URI
                org_and_repo, path = probe_path.split("//")
                path = Path(path)
                org, repo = org_and_repo.split("/")
            except ValueError:
                raise URLError(
                    f"Invalid URL format: {uri}. Use '//' to define 1 sub-directory "
                    "and specify at most 1 branch."
                )
            filesystem = fsspec.filesystem(protocol="github", org=org, repo=repo, sha=f"refs/heads/{branch}")
        case "charm":
            # Extract the charm names from the URI, stripping the leading "/"
            charms = [parsed_uri.netloc] + parsed_uri.path[1:].split("/")
            # Get each filesystem from the GitHub repo named charm(-k8s)-operator format
            for charm in charms:
                filesystem = fsspec.filesystem(
                    protocol="github", org="canonical", repo=f"{charm}-operator", sha=f"refs/heads/{branch}"
                )
                probes_path = Path("probes")
                try:
                    _get_filesystem(filesystem, probes_path, local_path, parsed_uri)
                except FileNotFoundError:
                    pass

                raise NotImplementedError
                probe = Probe(
                    name=probes_path.relative_to(destination).as_posix(),
                    category="from-gh",
                    uri=uri,
                    original_path=Path(path),
                    local_path=probe_path,
                )
            return probes
        case _:
            raise NotImplementedError

    try:
        _get_filesystem(filesystem, path, local_path, parsed_uri)
    except FileNotFoundError:
        return probes

    log.info(f"copying {path.as_posix()} to {local_path.as_posix()} recursively")

    if filesystem.isfile(path.as_posix()):
        probe_files = [local_path]
    else:
        probe_files: List[Path] = [f for f in local_path.rglob("*") if f.as_posix().endswith(".py")]

    for probe_path in probe_files:
        # NOTE: very naive category recognition
        category = None
        if ProbeCategory.STATUS.value in probe_path.as_posix():
            category = ProbeCategory.STATUS
        if ProbeCategory.BUNDLE.value in probe_path.as_posix():
            category = ProbeCategory.BUNDLE
        if ProbeCategory.SHOW_UNIT.value in probe_path.as_posix():
            category = ProbeCategory.SHOW_UNIT
        probe = Probe(
            name=probe_path.relative_to(destination).as_posix(),
            category=category,
            uri=uri,
            original_path=Path(path),
            local_path=probe_path,
        )
        log.info(f"Fetched probe: {probe}")
        probes.append(probe)

    return probes
