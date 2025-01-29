#!/usr/bin/env python3

"""Probe for juju show-unit."""

import sys

import yaml

if __name__ == "__main__":
    data = yaml.safe_load(sys.stdin)
    print("This probe always fails!", file=sys.stderr)
    exit(1)
