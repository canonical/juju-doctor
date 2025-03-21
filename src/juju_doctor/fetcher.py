#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Helper module to fetch probes from local or remote endpoints."""

import logging
from pathlib import Path
from typing import List

from juju_doctor.probes import Probe, ProbeFS

log = logging.getLogger(__name__)


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
                f for f in probe_fs.local_path.rglob("*") if f.as_posix().endswith(".py")
            ]

        probes = []
        for probe_path in probe_files:
            probe = Probe(
                name=probe_path.relative_to(probe_fs.destination).as_posix(),
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
            destination: the file path for the probes on the local FS.
            uri: a URI to a probe living somewhere.
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
