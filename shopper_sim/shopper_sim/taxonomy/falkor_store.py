"""FalkorDB backend for the journey graph (authoring path only).

The in-memory :class:`JourneyGraph` is the canonical, dependency-free
representation the engine and tests use. FalkorDB is an *optional* persistent
backend for the authoring path: you sync the canonical graph into FalkorDB to
query/visualise/extend it with Cypher, and you can load a graph back out of
FalkorDB into the same in-memory structure.

Design rules (consistent with the determinism contract):
  * FalkorDB is NEVER on the runtime scoring path. Compiled scenarios are frozen
    JSON; nothing in ``adapters``/``oracle``/``orchestrator`` imports this module.
  * ``falkordb`` is imported lazily so the engine and the whole offline test
    suite run without the client or a server.
  * Sync is deterministic: nodes and edges are written in sorted order, so the
    resulting graph is identical across runs.

Requires a running FalkorDB server (Redis protocol, default port 6379). Start
one with: ``docker run -p 6379:6379 -it --rm falkordb/falkordb``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .graph import Edge, EdgeKind, JourneyGraph, build_default_graph
from .registry import all_families


@dataclass(frozen=True)
class FalkorConfig:
    host: str = "localhost"
    port: int = 6379
    graph_name: str = "shopper_journey"
    username: str | None = None
    password: str | None = None


class FalkorJourneyStore:
    """Persists and queries the journey graph in FalkorDB.

    Thin wrapper over the ``falkordb`` client. Construction does not connect;
    the first operation opens the connection so import/instantiation stays cheap
    and offline-safe.
    """

    def __init__(self, config: FalkorConfig | None = None) -> None:
        self._config = config or FalkorConfig()
        self._db = None
        self._graph = None

    # -- connection --------------------------------------------------------

    def _connect(self):
        if self._graph is not None:
            return self._graph
        try:
            from falkordb import FalkorDB  # lazy import
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "falkordb is not installed; install with `pip install "
                "shopper-sim[graph]` to use the FalkorDB backend"
            ) from exc
        kwargs = {"host": self._config.host, "port": self._config.port}
        if self._config.username:
            kwargs["username"] = self._config.username
        if self._config.password:
            kwargs["password"] = self._config.password
        self._db = FalkorDB(**kwargs)
        self._graph = self._db.select_graph(self._config.graph_name)
        return self._graph

    def ping(self) -> bool:
        """Return True if a FalkorDB server is reachable, False otherwise."""
        try:
            g = self._connect()
            g.query("RETURN 1")
            return True
        except Exception:  # pragma: no cover - network dependent
            return False

    # -- sync (canonical -> FalkorDB) --------------------------------------

    def sync(self, graph: JourneyGraph | None = None, *, wipe: bool = True) -> int:
        """Write the canonical graph into FalkorDB. Returns the edge count.

        Deterministic: families and edges are written in sorted order. With
        ``wipe=True`` the named graph is cleared first so the result is an exact
        mirror of the in-memory graph.
        """
        graph = graph or build_default_graph()
        g = self._connect()
        if wipe:
            try:
                g.delete()
            except Exception:  # graph may not exist yet
                pass
            g = self._db.select_graph(self._config.graph_name)
            self._graph = g

        # Nodes: one per family, with its taxonomy metadata.
        for fam in all_families():
            g.query(
                "MERGE (f:Family {id: $id}) "
                "SET f.number = $number, f.name = $name, f.lifecycle = $lifecycle, "
                "f.layer = $layer, f.turns = $turns",
                {
                    "id": fam.id,
                    "number": fam.number,
                    "name": fam.name,
                    "lifecycle": fam.lifecycle.value,
                    "layer": fam.layer.value,
                    "turns": fam.turns.value,
                },
            )

        # Edges: typed relationships with weights.
        count = 0
        for edge in graph.all_edges():
            g.query(
                "MATCH (a:Family {id: $src}), (b:Family {id: $dst}) "
                "MERGE (a)-[r:REL {kind: $kind}]->(b) "
                "SET r.weight = $weight",
                {
                    "src": edge.src,
                    "dst": edge.dst,
                    "kind": edge.kind.value,
                    "weight": edge.weight,
                },
            )
            count += 1
        return count

    # -- load (FalkorDB -> canonical) --------------------------------------

    def load(self) -> JourneyGraph:
        """Reconstruct an in-memory :class:`JourneyGraph` from FalkorDB."""
        g = self._connect()
        graph = JourneyGraph()
        result = g.query(
            "MATCH (a:Family)-[r:REL]->(b:Family) "
            "RETURN a.id, b.id, r.kind, r.weight "
            "ORDER BY a.id, b.id, r.kind"
        )
        for src, dst, kind, weight in result.result_set:
            graph.add_edge(src, dst, EdgeKind(kind), float(weight))
        return graph

    # -- queries (authoring conveniences) ----------------------------------

    def journeys_into(self, family_id: str, max_depth: int = 4) -> list[list[str]]:
        """All REQUIRES/PRECEDES paths that lead into a family (Cypher-side).

        Useful for authoring: shows every prerequisite chain a multistep family
        depends on, computed by the graph engine rather than in Python.
        """
        g = self._connect()
        result = g.query(
            "MATCH p = (start:Family)-[:REL*1.."
            + str(int(max_depth))
            + " {}]->(target:Family {id: $id}) "
            "RETURN [n IN nodes(p) | n.id] AS path ORDER BY size(path)",
            {"id": family_id},
        )
        return [row[0] for row in result.result_set]
