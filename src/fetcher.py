#!/usr/bin/env python3


import fsspec
from pathlib import Path
from urllib.parse import urlparse
from types import SimpleNamespace
from urllib.error import URLError
import sys


class Fetcher(object):
    """A deployment configuration validator for juju.

    TODO Potential schema:
        --probe gh://canonical/grafana-k8s//probes@feature/probes
    """

    def __init__(self, destination: Path):
        self.destination = destination
        self.meta = self.meta = SimpleNamespace(
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
        if Path(probe).is_file() or Path(probe).is_dir():
            self.meta.protocol = "file"
            self.meta.path = Path(probe)

        else:
            parsed_url = urlparse(probe)
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

    def fetch_probes(self):
        if self.meta.protocol == "file":
            fs = self.fsspec_fs_local()
            self.copy_files(fs)
        elif self.meta.protocol == "github":
            fs = self.fsspec_fs_gh()
            self.copy_files(fs)
        else:
            raise NotImplementedError

    def fsspec_fs_gh(self):
        return fsspec.filesystem(
            self.meta.protocol,
            org=self.meta.org,
            repo=self.meta.repo,
            sha=f"refs/heads/{self.meta.ref}",
        )

    def fsspec_fs_local(self):
        return fsspec.filesystem(self.meta.protocol)

    def copy_files(self, fs):
        self.destination.mkdir(exist_ok=True, parents=True)
        # If path ends with a "/", it will be assumed to be a directory
        # Can submit a list of paths, which may be glob-patterns and will be expanded.
        fs.get(str(self.meta.path), self.destination.as_posix(), recursive=True)
        print(f"Probes located at: {self.destination}")


def main():
    print("probes-fetcher started.")
    probe = sys.argv[1]
    fetcher = Fetcher(Path("/tmp/fake/probes"))
    fetcher.run(probe)
    print("probes-fetcher finished.")


if __name__ == "__main__":
    main()
