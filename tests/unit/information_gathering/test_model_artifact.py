
from unittest.mock import MagicMock, mock_open, patch

import yaml

from juju_doctor.artifacts import ModelArtifact

JUJU_STATUS = """
model:
  name: sixx
  type: caas
  controller: k8s
  cloud: microk8s
  region: localhost
  version: 4.0-beta4
  model-status:
    current: available
    since: 06 Mar 2025 09:29:06+01:00
machines: {}
applications:
  k6:
    charm: local:k6-k8s-60
    base:
      name: ubuntu
      channel: "24.04"
    charm-origin: local
    charm-name: k6-k8s
    charm-rev: 60
    charm-version: eda5e60
    scale: 1
    provider-id: 61ff2c1a-a6ee-4892-be6f-e6a359779eee
    address: 10.152.183.237
    exposed: false
    application-status:
      current: active
      since: 14 Mar 2025 11:19:38+01:00
    relations:
      k6:
      - related-application: k6
        interface: k6_peers
        scope: global
    units:
      k6/0:
        workload-status:
          current: active
          since: 14 Mar 2025 11:19:38+01:00
        juju-status:
          current: idle
          since: 19 Mar 2025 09:22:46+01:00
          version: 4.0-beta4
        leader: true
        address: 10.1.15.172
        provider-id: k6-0
    endpoint-bindings:
      "": alpha
      k6: alpha
storage: {}
controller:
  timestamp: 10:53:51+01:00
"""
JUJU_EXPORT_BUNDLE = """
bundle: kubernetes
applications:
  k6:
    charm: local:k6-k8s-60
    scale: 1
    options:
      load-test: |
        import loki from 'k6/x/loki';
        import { check, group, sleep } from 'k6';
        import { vu } from 'k6/execution';

        // 'fake' user is the default for disabled multi-tenancy
        // const conf = loki.Config("http://fake@10.123.158.222/loadky-loki-0");


        export const options = {
           vus: 2000, // thousands of small edge devices
           duration: "30m",
        }

        export default function () {
           // let streams = randInt(2, 8);
           const client = getLokiClient(vu.idInTest.toString())
           const streams = 1 // How many log streams per client
           const minSize = 256  // log line minimum size: 1mb (now 1kb)
           const maxSize = 1024  // log line maximum size: 2mb (now 2kb)
           const thinkTime = randInt(1, 3)
           const res = client.pushParameterized(streams, minSize, maxSize)
           // check(res, { 'successful push': (res) => res.status == 200 });
           sleep(thinkTime)
        };

        function randInt(min, max) {
          return Math.floor(Math.random() * (max - min + 1) + min);
        };

        function getLokiClient(vuLabel) {
           const labels = loki.Labels({
              "format": ["json", "logfmt"],
           })
           const conf = loki.Config("http://fake@10.1.15.152:3100", 10000, 0.9, null, labels);
           const client = loki.Client(conf);
           return client
        }
    constraints: arch=amd64
"""

JUJU_SHOW_UNIT = """
k6/0:
  opened-ports: []
  charm: local:k6-k8s-60
  leader: true
  life: alive
  relation-info:
  - relation-id: 2
    endpoint: k6
    related-endpoint: k6
    application-data:
      k6: '{}'
    local-unit:
      in-scope: true
      data:
        egress-subnets: 10.152.183.237/32
        ingress-address: 10.152.183.237
        private-address: 10.152.183.237
  provider-id: k6-0
  address: 10.1.15.172
"""

FILES = {"status.yaml": JUJU_STATUS, "bundle.yaml": JUJU_EXPORT_BUNDLE, "show-unit.yaml": JUJU_SHOW_UNIT}


def test_model_artifact_parsing_from_file():
    def _open_side_effect(filename, *args, **kwargs):
        if filename in FILES:
            mock = mock_open(read_data=FILES[filename])
            return mock()
        raise FileNotFoundError(f"No such file: '{filename}'")

    with patch("builtins.open", side_effect=_open_side_effect):
        model_artifact = ModelArtifact.from_files(
            status_file="status.yaml", bundle_file="bundle.yaml", show_unit_file="show-unit.yaml"
        )
        assert model_artifact.status == yaml.safe_load(JUJU_STATUS)
        assert model_artifact.bundle == yaml.safe_load(JUJU_EXPORT_BUNDLE)
        assert model_artifact.show_units == yaml.safe_load(JUJU_SHOW_UNIT)


def test_model_artifact_parsing_from_live_model():
    def _juju_side_effect(command, *args, **kwargs):
        """Dashes `-` are not allowed in chained commands from the `sh` module."""
        if command == "export-bundle":
            return JUJU_EXPORT_BUNDLE
        if command == "show-unit":
            return JUJU_SHOW_UNIT
        return ""

    with patch("sh.juju", MagicMock()) as juju_mock:
        juju_mock.status.return_value = JUJU_STATUS
        juju_mock.side_effect = _juju_side_effect
        model_artifact = ModelArtifact.from_live_model(model="some-model")
        assert model_artifact.status == yaml.safe_load(JUJU_STATUS)
        assert model_artifact.bundle == yaml.safe_load(JUJU_EXPORT_BUNDLE)
        assert model_artifact.show_units == yaml.safe_load(JUJU_SHOW_UNIT)


def test_model_artifacts_is_equivalent():
    def _open_side_effect(filename, *args, **kwargs):
        if filename in FILES:
            mock = mock_open(read_data=FILES[filename])
            return mock()
        raise FileNotFoundError(f"No such file: '{filename}'")

    def _juju_side_effect(command, *args, **kwargs):
        if command == "export-bundle":
            return JUJU_EXPORT_BUNDLE
        if command == "show-unit":
            return JUJU_SHOW_UNIT
        return ""

    with patch("builtins.open", side_effect=_open_side_effect):
        with patch("sh.juju", MagicMock()) as juju_mock:
            juju_mock.status.return_value = JUJU_STATUS
            juju_mock.side_effect = _juju_side_effect

            from_files_artifact = ModelArtifact.from_files(
                status_file="status.yaml", bundle_file="bundle.yaml", show_unit_file="show-unit.yaml"
            )

            from_live_model_artifact = ModelArtifact.from_live_model(model="some-model")
            assert from_files_artifact == from_live_model_artifact
