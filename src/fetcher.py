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
from urllib.parse import urlparse

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
    path: Path

    def is_category(self, category: ProbeCategory) -> bool:
        """Check if the Probe belongs to the specified category."""
        return self.category == category


def fetch_probes(uri: str, destination: Path) -> List[Probe]:
    """Fetch probes from a source to a local directory.

    Args:
        uri: a URI to a probe living somewhere.
            Currently only supports 'github://' with Terraform notation and 'file://'.
        destination: the folder where to save the probes.
    """
    probes = []
    parsed_uri = urlparse(uri)
    subfolder = f"{parsed_uri.netloc}{parsed_uri.path}".replace("/", "_").replace(":", "_")
    local_path = destination / subfolder

    match parsed_uri.scheme:
        case "file":
            path = Path(f"{parsed_uri.netloc}{parsed_uri.path}")
            filesystem = fsspec.filesystem(protocol="file")
            local_path.mkdir(parents=True, exist_ok=True)
        case "github":
            try:
                # Extract the org and repository from the URI
                org_and_repo, path = uri.removeprefix("github://").split("//")
                org, repo = org_and_repo.split("/")
                # Extract the branch name if present
                branch = "main"
                if "@" in path:
                    path, branch = path.split("@")
                path = Path(path)
            except ValueError:
                raise URLError(
                    f"Invalid URL format: {uri}. Use '//' to define 1 sub-directory "
                    "and specify at most 1 branch."
                )
            filesystem = fsspec.filesystem(
                protocol="github", org=org, repo=repo, sha=f"refs/heads/{branch}"
            )
        case _:
            raise NotImplementedError

    # If path ends with a "/", it will be assumed to be a directory
    # Can submit a list of paths, which may be glob-patterns and will be expanded.
    filesystem.get(path.as_posix(), local_path.as_posix(), recursive=True)

    if local_path.is_file():
        probe_files = [local_path.as_posix()]
    else:
        probe_files = filesystem.glob(f"{path.as_posix()}/**/*.py")

    for path in probe_files:
        # NOTE: very naive category recognition
        category = None
        if ProbeCategory.STATUS.value in path:
            category = ProbeCategory.STATUS
        if ProbeCategory.BUNDLE.value in path:
            category = ProbeCategory.BUNDLE
        if ProbeCategory.SHOW_UNIT.value in path:
            category = ProbeCategory.SHOW_UNIT
        probe = Probe(name=Path(path).name, category=category, uri=uri, path=Path(path))
        log.info(f"Fetched probe: {probe}")
        probes.append(probe)

    return probes
