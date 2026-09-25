from importlib import resources
from unittest.mock import mock_open, patch

import pytest
import yaml
from jubilant import ModelInfo, Status, UnitInfo

from juju_doctor.artifacts import ArtifactError, Artifacts, ModelArtifact, read_file

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

FILES = {
    "status.yaml": JUJU_STATUS,
    "bundle.yaml": JUJU_EXPORT_BUNDLE,
    "show-unit.yaml": JUJU_SHOW_UNIT,
}


def _open_side_effect(filename, *args, **kwargs):
    if filename in FILES:
        mock = mock_open(read_data=FILES[filename])
        return mock()
    raise FileNotFoundError(f"No such file: '{filename}'")


def test_model_artifact_parsing_from_file():
     with patch("builtins.open", side_effect=_open_side_effect):
        model_artifact = ModelArtifact.from_files(
            status_file="status.yaml", bundle_file="bundle.yaml", show_unit_file="show-unit.yaml"
        )
        assert model_artifact.status == Status._from_dict(yaml.safe_load(JUJU_STATUS))
        assert model_artifact.bundle == yaml.safe_load(JUJU_EXPORT_BUNDLE)
        assert model_artifact.show_units == {
            "k6/0": UnitInfo._from_dict(yaml.safe_load(JUJU_SHOW_UNIT)["k6/0"])
        }


def test_only_provided_artifacts():
    with patch("builtins.open", side_effect=_open_side_effect):
        # GIVEN only some (omitting show_unit) artifacts are provided
        status_artifact = ModelArtifact.from_files(status_file="status.yaml")
        bundle_artifact = ModelArtifact.from_files(bundle_file="bundle.yaml")
        # WHEN the artifacts are aggregated
        artifacts = Artifacts(
            {
                "some_path/status.yaml": status_artifact,
                "some_path/bundle.yaml": bundle_artifact,
            }
        )
        # THEN the ommitted artifact is empty
        assert not artifacts.show_unit
        assert artifacts.status
        assert artifacts.bundle


def test_model_artifact_parsing_from_live_model():
    def _juju_side_effect(command, *args, **kwargs):
        """Dashes `-` are not allowed in chained commands from the `sh` module."""
        if command == "export-bundle":
            return JUJU_EXPORT_BUNDLE
        if command == "show-unit":
            return JUJU_SHOW_UNIT
        return ""

    with patch("juju_doctor.artifacts.sh") as sh_mock:
        sh_mock.juju.status.return_value = JUJU_STATUS
        sh_mock.juju.side_effect = _juju_side_effect
        model_artifact = ModelArtifact.from_live_model(model="some-model")
        assert model_artifact.status == Status._from_dict(yaml.safe_load(JUJU_STATUS))
        assert model_artifact.bundle == yaml.safe_load(JUJU_EXPORT_BUNDLE)
        assert model_artifact.show_units == {
            "k6/0": UnitInfo._from_dict(yaml.safe_load(JUJU_SHOW_UNIT)["k6/0"])
        }


def test_model_artifacts_are_equivalent():
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
        with patch("juju_doctor.artifacts.sh") as sh_mock:
            sh_mock.juju.status.return_value = JUJU_STATUS
            sh_mock.juju.side_effect = _juju_side_effect

            from_files_artifact = ModelArtifact.from_files(
                status_file="status.yaml",
                bundle_file="bundle.yaml",
                show_unit_file="show-unit.yaml",
            )

            from_live_model_artifact = ModelArtifact.from_live_model(model="some-model")
            assert from_files_artifact == from_live_model_artifact


SHOW_MODEL_FILE = "tests/resources/artifacts/show-model.yaml"
DUMP_MODEL_FILE = "tests/resources/artifacts/dump-model.yaml"


def test_show_model_artifact_from_file():
    artifact = ModelArtifact.from_files(show_model_file=SHOW_MODEL_FILE)
    assert artifact.show_model is not None
    assert isinstance(artifact.show_model, ModelInfo)
    assert artifact.show_model.name == "sixx"
    assert artifact.show_model.model_uuid == "0d9f03ae-cc37-4f68-8cae-3a6a6590a538"


def test_show_model_artifact_aggregation():
    artifact = ModelArtifact.from_files(show_model_file=SHOW_MODEL_FILE)
    artifacts = Artifacts({"sixx": artifact})
    assert artifacts.show_model["sixx"].short_name == "sixx"


def test_model_dump_artifact_from_file():
    artifact = ModelArtifact.from_files(model_dump_file=DUMP_MODEL_FILE)
    assert artifact.model_dump is not None
    assert artifact.model_dump["applications"]["applications"]
    artifacts = Artifacts({"cos": artifact})
    assert artifacts.model_dump["cos"]["type"] == "caas"


def test_py_typed_marker_is_shipped():
    assert resources.files("juju_doctor").joinpath("py.typed").is_file()


def test_read_file_is_lenient_for_missing_files():
    # The lenient reader is used for optional probe files and returns None.
    assert read_file("does-not-exist.yaml") is None


def test_from_files_missing_file_raises():
    with pytest.raises(ArtifactError):
        ModelArtifact.from_files(status_file="does-not-exist.yaml")


def test_from_files_empty_file_raises():
    with patch("builtins.open", mock_open(read_data="")):
        with pytest.raises(ArtifactError):
            ModelArtifact.from_files(status_file="empty.yaml")


def test_from_files_invalid_status_raises():
    with patch("builtins.open", mock_open(read_data="not-a-status: true")):
        with pytest.raises(ArtifactError):
            ModelArtifact.from_files(status_file="invalid.yaml")


def test_from_live_model_requires_status():
    with patch("juju_doctor.artifacts.sh") as sh_mock:
        sh_mock.juju.status.side_effect = RuntimeError("no controller connection")
        with pytest.raises(ArtifactError):
            ModelArtifact.from_live_model(model="some-model")


def test_show_unit_skips_malformed_units():
    show_units = """
k6/0:
  opened-ports: []
  charm: local:k6-k8s-60
  leader: true
k6/1:
  not-a-unit: true
"""
    with patch("builtins.open", mock_open(read_data=show_units)):
        artifact = ModelArtifact.from_files(show_unit_file="show-unit.yaml")
    # The malformed unit is skipped, the valid one is kept.
    assert list(artifact.show_units or {}) == ["k6/0"]


def test_show_unit_all_malformed_raises():
    show_units = """
k6/0:
  not-a-unit: true
"""
    with patch("builtins.open", mock_open(read_data=show_units)):
        with pytest.raises(ArtifactError):
            ModelArtifact.from_files(show_unit_file="show-unit.yaml")


def test_from_live_model_tolerates_removed_commands():
    def _juju_side_effect(command, *args, **kwargs):
        if command == "export-bundle":
            raise RuntimeError("export-bundle was removed in Juju 4")
        if command == "show-unit":
            return JUJU_SHOW_UNIT
        return ""

    with patch("juju_doctor.artifacts.sh") as sh_mock:
        sh_mock.juju.status.return_value = JUJU_STATUS
        sh_mock.juju.side_effect = _juju_side_effect
        artifact = ModelArtifact.from_live_model(model="some-model")

    # The removed command is skipped, but the remaining artifacts are gathered.
    assert artifact.status == Status._from_dict(yaml.safe_load(JUJU_STATUS))
    assert artifact.bundle is None
    assert artifact.show_units == {
        "k6/0": UnitInfo._from_dict(yaml.safe_load(JUJU_SHOW_UNIT)["k6/0"])
    }
