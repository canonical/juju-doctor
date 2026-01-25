"""Mutually exclusive relations builtin plugin.

The probe checks that the given charm names (not application names!) do not have mutually
exclusive relations related. This could be useful when relations conflict with each other.

To call this builtin within a RuleSet YAML file:

```yaml
name: RuleSet
probes:
    - name: Mutually exclusive relations
      type: builtin/mutually-exclusive-relations
      with:
        - charm: opentelemetry-collector
          relations: [cos-agent, juju-info]
        - charm: opentelemetry-collector-k8s
          relations: [cos-agent, juju-info]
        - charm: grafana-agent
          relations: [cos-agent, juju-info]
        - charm: grafana-agent-k8s
          relations: [cos-agent, juju-info]
```
"""
from collections import defaultdict
from typing import Generator

import networkx as nx
from pydantic import BaseModel, ConfigDict, model_validator

from juju_doctor.artifacts import read_file


class MutuallyExclusiveRelations(BaseModel):
    """Schema for the `mutually-exclusive-relations` RuleSet definition."""

    model_config = ConfigDict(extra="forbid")

    charm: str
    relations: set[str]


def bundle(juju_bundles: dict[str, dict], **kwargs):
    """Bundle assertion for mutually exclusive relations.

    >>> bundle({"some-model": test_bundle1()}, **{"charm": "a-charm", "relations": {"r", "q"}})  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: Mutually exclusive relations found: [('a', 'b', ...
    """
    spec = MutuallyExclusiveRelations(**kwargs)

    for bundle_name, bundle_dict in juju_bundles.items():
        graph, apps_by_charm = from_bundle(bundle_dict)
        apps = apps_by_charm[spec.charm]
        for app in apps:
            if violations := mutually_exclusive_relations_by_app_name(graph, app, spec.relations):
                raise Exception(f"Mutually exclusive relations found: {violations}")


# ==========================
# Bundle models
# ==========================

class Application(BaseModel):
    charm: str | None = None
    # channel: str | None = None
    # revision: int | None = None
    # resources: dict[str, int] = Field(default_factory=dict)
    # scale: int | None = None
    # constraints: str | None = None
    # storage: dict[str, str] = Field(default_factory=dict)
    # trust: bool | None = None
    model_config = ConfigDict(extra="allow")


class Endpoint(BaseModel):
    app: str
    relation_name: str
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def from_str(cls, value):
        if isinstance(value, str):
            if value.count(":") != 1:
                raise ValueError("Endpoint must be in the form 'app:relation'")
            app, relation = value.split(":", 1)
            return {"app": app, "relation_name": relation}
        return value


class Relation(BaseModel):
    # interface: str  # `juju status` does not give interface
    provider: Endpoint
    requirer: Endpoint
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def parse_pair(cls, value):
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return {"provider": value[0], "requirer": value[1]}
        return value


class Bundle(BaseModel):
    applications: dict[str, Application | None]
    relations: list[Relation]
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def normalize_applications(cls, value):
        if isinstance(value, dict):
            applications = value.get("applications")
            if isinstance(applications, dict):
                for name, config in applications.items():
                    config = config or {}
                    # If config was None (immutable), then we need to assign it now
                    applications[name] = config
        return value


# ==========================
# Helper functions
# ==========================

def from_bundle(bundle_: dict) -> tuple[nx.MultiGraph, dict[str, list[str]]]:
    b = Bundle.model_validate(bundle_)
    graph = nx.MultiGraph()
    # "Mutually exclusive relations" is usually applicable to _charms_ rather than _applications_.
    # Since the nodes in a relation graph are app names, we group by charm to retrieve efficiently from the graph.
    apps_by_charm: dict[str, list[str]] = defaultdict(list)

    # First, populate the graph with all the applications, because we can only add node attributes with "add_node"
    for app, config in b.applications.items():
        graph.add_node(app, **config.model_dump())
        if config.charm:
            apps_by_charm[config.charm].append(app)

    # Now add edges
    for relation in b.relations:
        graph.add_edge(relation.provider.app, relation.requirer.app, relation=relation)

    return graph, apps_by_charm


def edges_by_neighbor(graph: nx.MultiGraph, node, edge_attribute_name) -> dict:
    if node not in graph:
        return {}

    adj = graph[node]
    return {neigh: [v[edge_attribute_name] for v in adj[neigh].values()] for neigh in adj}


def edges_by_neighbor_gen(graph: nx.MultiGraph, node, edge_attribute_name) -> Generator[tuple, None, None]:
    """>>> g = nx.MultiGraph()
    >>> g.add_edge("a", "b", label="p")
    0
    >>> g.add_edge("a", "b", label="q")
    1
    >>> g.add_edge("a", "c", label="r")
    0
    >>> gen = edges_by_neighbor_gen(g, "a", "label")
    >>> list(gen)
    [('b', ['p', 'q']), ('c', ['r'])]
    """
    if node in graph:
        adj = graph[node]
        for neigh in adj:
            yield neigh, [v[edge_attribute_name] for v in adj[neigh].values()]


def mutually_exclusive_relations_by_app_name(graph, node_name: str, mutually_exclusive_relations: set[str]) -> list:
    violations = []
    for neigh, edges in edges_by_neighbor_gen(graph, node_name, "relation"):
        # List of endpoints going from node_name to neigh
        endpoints = [edge.provider.relation_name for edge in edges if edge.provider.app == node_name] + [
            edge.requirer.relation_name for edge in edges if edge.requirer.app == node_name
        ]
        if len(intersection := mutually_exclusive_relations.intersection(endpoints)) > 1:
            violations.append((node_name, neigh, intersection))

    return violations


# ==========================
# Test helpers
# ==========================
from textwrap import dedent

import yaml


def test_bundle1():
    """Doctest input."""
    return yaml.safe_load(dedent(
    """
    applications:
      a:
        charm: a-charm
      b:
        charm: b-charm
      c:
        charm: c-charm
      x:
        charm: x-charm
      y:
        charm: y-charm
      z:
        charm: z-charm
    relations:
      - [a:r, b:rr]
      - [a:q, b:qq]
      - [x:r, y:rr]
      - [x:q, y:qq]
    """
    ))
