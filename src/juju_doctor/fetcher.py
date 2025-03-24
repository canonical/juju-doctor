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


        return Fetcher._build_probes(probe_fs)
