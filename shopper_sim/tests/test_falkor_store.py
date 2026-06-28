"""Tests for the FalkorDB journey-graph backend.

These skip cleanly when no FalkorDB server is reachable (the default in CI and
the offline sandbox), and exercise a real sync/load round-trip when one is.
Start a server with: docker run -p 6379:6379 -it --rm falkordb/falkordb
"""

from __future__ import annotations

import pytest

falkordb = pytest.importorskip("falkordb")

from shopper_sim.taxonomy.falkor_store import FalkorConfig, FalkorJourneyStore
from shopper_sim.taxonomy.graph import build_default_graph


@pytest.fixture(scope="module")
def store():
    s = FalkorJourneyStore(FalkorConfig())
    if not s.ping():
        pytest.skip("no FalkorDB server reachable on localhost:6379")
    return s


def test_ping_returns_bool_without_server():
    # ping must never raise even when nothing is listening.
    s = FalkorJourneyStore(FalkorConfig(port=6390))  # unlikely port
    assert s.ping() is False


def test_sync_then_load_roundtrip(store):
    canonical = build_default_graph()
    written = store.sync(canonical)
    assert written == len(canonical.all_edges())

    loaded = store.load()
    assert loaded.nodes() == canonical.nodes()
    # Edge sets match (src, dst, kind, weight).
    a = {(e.src, e.dst, e.kind.value, e.weight) for e in canonical.all_edges()}
    b = {(e.src, e.dst, e.kind.value, e.weight) for e in loaded.all_edges()}
    assert a == b


def test_journeys_into_returns_prerequisite_paths(store):
    store.sync()
    paths = store.journeys_into("refunds", max_depth=4)
    # refunds depends on return_initiation in the default graph, so at least one
    # path should end at refunds.
    assert any(p[-1] == "refunds" for p in paths)


# -- server-free validation of the Cypher generation ----------------------

class _FakeResult:
    def __init__(self, rows):
        self.result_set = rows


class _FakeGraph:
    """Records queries and returns canned results, so we can validate the
    backend's Cypher/parameters without a live server."""

    def __init__(self):
        self.queries = []

    def query(self, q, params=None):
        self.queries.append((q, params or {}))
        # emulate a load() round-trip with two edges
        if "RETURN a.id, b.id" in q:
            return _FakeResult([
                ["tracking", "order_confirmation", "requires", 1.0],
                ["return_initiation", "refunds", "escalates_to", 1.5],
            ])
        return _FakeResult([])

    def delete(self):  # for wipe
        self.queries.append(("DELETE_GRAPH", {}))


def test_sync_emits_node_and_edge_cypher_with_params(monkeypatch):
    s = FalkorJourneyStore(FalkorConfig())
    fake = _FakeGraph()
    # bypass real connection
    s._graph = fake
    s._db = type("DB", (), {"select_graph": lambda self, name: fake})()
    canonical = build_default_graph()

    count = s.sync(canonical, wipe=False)
    assert count == len(canonical.all_edges())
    # Node MERGEs carry an id param; edge MERGEs carry src/dst/kind/weight.
    node_qs = [q for q in fake.queries if "MERGE (f:Family" in q[0]]
    edge_qs = [q for q in fake.queries if "MERGE (a)-[r:REL" in q[0]]
    assert len(node_qs) == 52
    assert len(edge_qs) == count
    assert all({"src", "dst", "kind", "weight"} <= set(p) for _, p in edge_qs)


def test_load_reconstructs_graph_from_cypher_rows():
    s = FalkorJourneyStore(FalkorConfig())
    fake = _FakeGraph()
    s._graph = fake
    loaded = s.load()
    edges = {(e.src, e.dst, e.kind.value) for e in loaded.all_edges()}
    assert ("tracking", "order_confirmation", "requires") in edges
    assert ("return_initiation", "refunds", "escalates_to") in edges
