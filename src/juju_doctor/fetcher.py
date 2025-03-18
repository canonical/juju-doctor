#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Helper module to fetch probes from local or remote endpoints."""

import logging
from pathlib import Path
from typing import List
from urllib.error import URLError
from urllib.parse import ParseResult, urlparse

import fsspec

from juju_doctor.probes import Probe

log = logging.getLogger(__name__)


class Fetcher(object):
    """A fetcher which uses protocols for obtaining a remote FS to copy to a local one."""

    def __init__(self, destination: Path):
        """Build a fetcher object.

        Args:
            destination: the file path for the probes on the local FS.
        """
        self.destination = destination

    def _get_filesystem(
        self, filesystem: fsspec.AbstractFileSystem, path: Path, local_path: Path, parsed_uri: ParseResult
    ):
        try:
            # If path ends with a "/", it will be assumed to be a directory
            # Can submit a list of paths, which may be glob-patterns and will be expanded.
            # https://github.com/fsspec/filesystem_spec/blob/master/docs/source/copying.rst
            filesystem.get(path.as_posix(), local_path.as_posix(), recursive=True, auto_mkdir=True)
        except FileNotFoundError as e:
            log.warning(
                f"{e} file not found when attempting to copy '{path.as_posix()}' to '{local_path.as_posix()}'"
            )
            raise

    def _build_probes(
        self, filesystem: fsspec.AbstractFileSystem, uri: str, path: Path, local_path: Path
    ) -> List[Probe]:
        if filesystem.isfile(path.as_posix()):
            probe_files = [local_path]
        else:
            probe_files: List[Path] = [f for f in local_path.rglob("*") if f.as_posix().endswith(".py")]

        probes = []
        for probe_path in probe_files:
            probe = Probe(
                name=probe_path.relative_to(self.destination).as_posix(),
                uri=uri,
                original_path=Path(path),
                path=probe_path,
            )
            log.info(f"Fetched probe: {probe}")
            probes.append(probe)

        return probes

    def fetch_probes(self, uri: str) -> List[Probe]:
        """Fetch probes from a source to a local directory.

        Args:
            uri: a URI to a probe living somewhere.
                Currently only supports:
                - 'github://' with Terraform notation
                - 'file://'
                - 'charm://' for fetching from charm(-k8s)-operator remotes
        """
        parsed_uri = urlparse(uri)
        probe_path = parsed_uri.netloc + parsed_uri.path
        subfolder = probe_path.replace("/", "_")
        local_path = self.destination / subfolder
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
                filesystem = fsspec.filesystem(
                    protocol="github", org=org, repo=repo, sha=f"refs/heads/{branch}"
                )
            case _:
                raise NotImplementedError

        try:
            self._get_filesystem(filesystem, path, local_path, parsed_uri)
        except FileNotFoundError:
            pass

        log.info(f"copying {path.as_posix()} to {local_path.as_posix()} recursively")

        return self._build_probes(filesystem, uri, path, local_path)
