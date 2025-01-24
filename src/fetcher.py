#!/usr/bin/env python3


import fsspec
from pathlib import Path
from urllib.parse import urlparse
import argparse
from types import SimpleNamespace
from urllib.error import URLError


class Fetcher(object):
    """A deployment configuration validator for juju.

    TODO Potential schema:
        --probe gh://canonical/grafana-k8s//probes@feature/probes
    """

    def __init__(self, destination: Path):
        self.destination = destination
        self.meta = self.meta = SimpleNamespace(
            is_file=False,
            path=Path(),
            ref="",
            org="",
            repo="",
            url="",
            protocol="unknown",
        )

    def run(self, probe: str):
        self.parse_tf_notation_into_components(probe)
        self.fetch_probes()

    def parse_tf_notation_into_components(self, probe: str) -> SimpleNamespace:
        if Path(probe).is_file():
            self.meta.is_file = True
            self.meta.path = Path(probe)
        else:
            parsed_url = urlparse(probe)
            print(parsed_url)
            self.meta.is_file = False
            split_path = parsed_url.path.split("//")
            if len(split_path) != 2:
                # TF subdir notation violation
                # https://developer.hashicorp.com/terraform/language/modules/sources#modules-in-package-sub-directories
                raise URLError(
                    f"Invalid URL format: {split_path[0]}. Use '//' to define at least 1 sub-directory"
                )
            context = [part for part in split_path[0].split("/") if part]
            self.meta.org = context[0]
            if len(context) > 1:
                self.meta.repo = context[1]
            self.meta.url = f"{parsed_url.scheme}://{parsed_url.netloc}/{self.meta.org}/{self.meta.repo}"
            self.meta.ref = parsed_url.query.replace("ref=", "")
            self.meta.path = Path(split_path[1])
            if "github" in self.meta.url:
                self.meta.protocol = "github"
        print(self.meta)

    def fetch_probes(self):
        if self.meta.is_file:
            raise NotImplementedError
        else:
            if self.meta.protocol == "unknown":
                raise NotImplementedError
            self.create_fs()

    def create_fs(self):
        self.destination.mkdir(exist_ok=True, parents=True)
        fs = fsspec.filesystem(
            self.meta.protocol,
            org=self.meta.org,
            repo=self.meta.repo,
            sha=f"refs/heads/{self.meta.ref}",
        )
        # If path ends with a "/", it will be assumed to be a directory
        # Can submit a list of paths, which may be glob-patterns and will be expanded.
        fs.get(str(self.meta.path), self.destination.as_posix(), recursive=True)
        print(f"Probes located at: {self.destination}")


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        "--probe", required=False, help="URL of a repository where the probe exists"
    )

    args = parser.parse_args()

    return args


def main():
    opts = parse_args()
    print("probes-fetcher started.")
    fetcher = Fetcher(Path("/tmp/fake/probes"))
    fetcher.run(opts.probe)
    print("probes-fetcher finished.")


if __name__ == "__main__":
    main()
