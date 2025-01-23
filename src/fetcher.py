#!/usr/bin/env python3


import fsspec
from pathlib import Path
import shutil
import argparse
import os
import sys
import tempfile
import requests


class Fetcher(object):
    """A deployment configuration validator for juju.

    1. Can we assume probes exist in GH? What about launchpad
    2. Can we use // TF subdir notation?
    3. Can we use @ for branch notation?
    4. --probe gh://canonical/grafana-k8s//probes@feature/probes
        - This is not intuitive, but could work
    5. Probes are copied to /tmp/fake/probes
    
    """

    def __init__(self, opts):
        self.opts = opts

    def run(self):
        if self.opts.probe:
            self.fetch_probe()
        elif self.opts.probes_dir:
            self.fetch_probes_dir()
        elif self.opts.branch:
            self.fetch_probe()

    def download_file(self, url):
        # TODO Consider converting automatically to https://raw.githubusercontent.com
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            sys.exit(1)

    def save_to_tempfile(self, content):
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".py"
        ) as temp_file:
            temp_file.write(content)
            return temp_file.name

    def fetch_probe(self):
        probe = self.download_file(self.opts.probe)
        filename = self.save_to_tempfile(probe)
        print(filename)
        os.remove(filename)  # TODO Remove after done testing

    def fetch_probes_dir(self):
        # TODO Make this an input
        destination = Path("/tmp") / "fake" / "probes"
        destination.mkdir(exist_ok=True, parents=True)
        fs = fsspec.filesystem("github", org="canonical", repo=self.opts.probes_dir, sha=f"refs/heads/{self.opts.branch}")
        # If path ends with a "/", it will be assumed to be a directory
        # Can submit a list of paths, which may be glob-patterns and will be expanded.
        fs.get("probes/", destination.as_posix(), recursive=True)
        print(f"Probes located at: {destination}")
        # shutil.rmtree(destination, ignore_errors=True)  # TODO Remove after done testing


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        "--probe", required=False, help="URL of a repository where the probe exists"
    )
    parser.add_argument(
        "--probes-dir",
        required=False,
        help="URL of a repository directory where multiple probe exists",
    )
    parser.add_argument("--branch", required=False, help="The repository branch")

    args = parser.parse_args()

    return args


def main():
    opts = parse_args()
    print("probes-fetcher started.")
    fetcher = Fetcher(opts)
    fetcher.run()
    print("probes-fetcher finished.")


if __name__ == "__main__":
    main()
