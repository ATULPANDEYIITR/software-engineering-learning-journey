from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from copy import deepcopy
from typing import Any, Iterable
import json
import time


class NoSQLType(Enum):
    DOCUMENT = "document"
    KEY_VALUE = "key-value"
    COLUMN = "column-family"
    GRAPH = "graph"


class ValidationError(ValueError):
    pass


class NotFoundError(KeyError):
    pass


@dataclass
class Document:
    document_id: str
    data: dict[str, Any]
    version: int = 1
    updated_at: float = field(default_factory=time.time)

    def update(self, changes: dict[str, Any]) -> None:
        if not isinstance(changes, dict):
            raise ValidationError("Document updates must be dictionaries.")
        self.data.update(deepcopy(changes))
        self.version += 1
        self.updated_at = time.time()


class DocumentStore:
    """Document-oriented storage: flexible nested records with field indexes."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._indexes: dict[str, dict[Any, set[str]]] = defaultdict(lambda: defaultdict(set))

    def _validate_id(self, document_id: str) -> None:
        if not document_id or not isinstance(document_id, str):
            raise ValidationError("Document ID must be a non-empty string.")

    def insert(self, document_id: str, data: dict[str, Any]) -> None:
        self._validate_id(document_id)
        if document_id in self._documents:
            raise ValidationError(f"Document {document_id!r} already exists.")
        if not isinstance(data, dict):
            raise ValidationError("Document data must be an object.")
        document = Document(document_id, deepcopy(data))
        self._documents[document_id] = document
        self._index_document(document)

    def _index_document(self, document: Document) -> None:
        for field_name, value in document.data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                self._indexes[field_name][value].add(document.document_id)

    def _remove_from_indexes(self, document: Document) -> None:
        for field_name, value_map in self._indexes.items():
            for value, ids in value_map.items():
                ids.discard(document.document_id)

    def update(self, document_id: str, changes: dict[str, Any]) -> None:
        document = self.get(document_id)
        self._remove_from_indexes(document)
        document.update(changes)
        self._index_document(document)

    def get(self, document_id: str) -> Document:
        try:
            return self._documents[document_id]
        except KeyError as exc:
            raise NotFoundError(document_id) from exc

    def find_by_field(self, field_name: str, value: Any) -> list[Document]:
        ids = self._indexes.get(field_name, {}).get(value, set())
        return [self._documents[i] for i in sorted(ids)]

    def delete(self, document_id: str) -> None:
        document = self.get(document_id)
        self._remove_from_indexes(document)
        del self._documents[document_id]

    def count(self) -> int:
        return len(self._documents)


class KeyValueStore:
    """Key-value storage with TTL and atomic compare-and-set semantics."""

    def __init__(self) -> None:
        self._values: dict[str, tuple[Any, float | None]] = {}

    def _validate_key(self, key: str) -> None:
        if not isinstance(key, str) or not key or len(key) > 256:
            raise ValidationError("Key must contain 1-256 characters.")

    def _purge_if_expired(self, key: str) -> None:
        record = self._values.get(key)
        if record is None:
            return
        _, expires_at = record
        if expires_at is not None and time.time() >= expires_at:
            del self._values[key]

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        self._validate_key(key)
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValidationError("TTL must be positive.")
        expires_at = None if ttl_seconds is None else time.time() + ttl_seconds
        self._values[key] = (deepcopy(value), expires_at)

    def get(self, key: str, default: Any = None) -> Any:
        self._validate_key(key)
        self._purge_if_expired(key)
        record = self._values.get(key)
        return default if record is None else deepcopy(record[0])

    def delete(self, key: str) -> bool:
        self._validate_key(key)
        self._purge_if_expired(key)
        return self._values.pop(key, None) is not None

    def compare_and_set(self, key: str, expected: Any, replacement: Any) -> bool:
        current = self.get(key)
        if current != expected:
            return False
        self.set(key, replacement)
        return True


@dataclass
class ColumnFamilyRow:
    row_key: str
    columns: dict[str, Any]


class ColumnFamilyStore:
    """Sparse wide-column model: rows can contain different column sets."""

    def __init__(self) -> None:
        self._rows: dict[str, ColumnFamilyRow] = {}

    def put(self, row_key: str, columns: dict[str, Any]) -> None:
        if not row_key:
            raise ValidationError("Row key cannot be empty.")
        if not isinstance(columns, dict) or not columns:
            raise ValidationError("At least one column is required.")
        row = self._rows.setdefault(row_key, ColumnFamilyRow(row_key, {}))
        row.columns.update(deepcopy(columns))

    def get(self, row_key: str, columns: Iterable[str] | None = None) -> dict[str, Any]:
        if row_key not in self._rows:
            raise NotFoundError(row_key)
        data = self._rows[row_key].columns
        if columns is None:
            return deepcopy(data)
        requested = set(columns)
        return {k: deepcopy(v) for k, v in data.items() if k in requested}

    def scan_column(self, column: str, expected: Any) -> list[ColumnFamilyRow]:
        return [
            ColumnFamilyRow(row.row_key, deepcopy(row.columns))
            for row in self._rows.values()
            if row.columns.get(column) == expected
        ]

    def delete_column(self, row_key: str, column: str) -> None:
        if row_key not in self._rows:
            raise NotFoundError(row_key)
        self._rows[row_key].columns.pop(column, None)


@dataclass(frozen=True)
class Node:
    node_id: str
    labels: frozenset[str]
    properties: dict[str, Any]


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relationship: str
    properties: dict[str, Any] = field(default_factory=dict)


class GraphStore:
    """Property graph with directed relationships and breadth-first traversal."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[Edge]] = defaultdict(list)

    def add_node(
        self,
        node_id: str,
        labels: Iterable[str],
        properties: dict[str, Any] | None = None,
    ) -> None:
        if not node_id or node_id in self.nodes:
            raise ValidationError("Node ID must be unique and non-empty.")
        self.nodes[node_id] = Node(
            node_id,
            frozenset(labels),
            deepcopy(properties or {}),
        )

    def add_edge(
        self,
        source: str,
        target: str,
        relationship: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise NotFoundError("Both edge endpoints must exist.")
        if not relationship:
            raise ValidationError("Relationship type cannot be empty.")
        self.edges[source].append(
            Edge(source, target, relationship, deepcopy(properties or {}))
        )

    def neighbors(self, node_id: str, relationship: str | None = None) -> list[Node]:
        if node_id not in self.nodes:
            raise NotFoundError(node_id)
        return [
            self.nodes[edge.target]
            for edge in self.edges.get(node_id, [])
            if relationship is None or edge.relationship == relationship
        ]

    def shortest_path(self, start: str, target: str) -> list[str] | None:
        if start not in self.nodes or target not in self.nodes:
            raise NotFoundError("Both nodes must exist.")
        queue = deque([start])
        previous: dict[str, str | None] = {start: None}

        while queue:
            current = queue.popleft()
            if current == target:
                path: list[str] = []
                while current is not None:
                    path.append(current)
                    current = previous[current]
                return list(reversed(path))

            for edge in self.edges.get(current, []):
                if edge.target not in previous:
                    previous[edge.target] = current
                    queue.append(edge.target)

        return None


def demonstrate_document_store() -> None:
    store = DocumentStore()
    store.insert(
        "u100",
        {
            "name": "Atul",
            "department": "R&D",
            "skills": ["Python", "PostgreSQL"],
            "security": {"clearance": "internal"},
        },
    )
    store.insert(
        "u101",
        {
            "name": "Maya",
            "department": "R&D",
            "skills": ["Java", "Graph"],
        },
    )
    store.update("u100", {"active": True})

    print("\nDOCUMENT STORE")
    print(json.dumps(store.get("u100").data, indent=2))
    print("R&D users:", [d.document_id for d in store.find_by_field("department", "R&D")])


def demonstrate_key_value_store() -> None:
    cache = KeyValueStore()
    cache.set("session:u100", {"authenticated": True}, ttl_seconds=30)
    print("\nKEY-VALUE STORE")
    print("Session:", cache.get("session:u100"))
    print("CAS success:", cache.compare_and_set(
        "counter", None, 1
    ))
    print("Counter:", cache.get("counter"))


def demonstrate_column_store() -> None:
    metrics = ColumnFamilyStore()
    metrics.put(
        "device:GNSS-01",
        {"region": "Lucknow", "temperature": 31.5, "signal_quality": 94},
    )
    metrics.put(
        "device:GNSS-02",
        {"region": "Delhi", "signal_quality": 87},
    )

    print("\nCOLUMN-FAMILY STORE")
    print("Sparse row:", metrics.get("device:GNSS-02"))
    print(
        "Strong signal devices:",
        [row.row_key for row in metrics.scan_column("signal_quality", 94)],
    )


def demonstrate_graph_store() -> None:
    graph = GraphStore()
    graph.add_node("repo", ["Repository"], {"name": "security-platform"})
    graph.add_node("team", ["Team"], {"name": "R&D"})
    graph.add_node("service", ["Service"], {"name": "telemetry"})
    graph.add_node("database", ["Database"], {"name": "events"})
    graph.add_edge("team", "repo", "OWNS")
    graph.add_edge("repo", "service", "CONTAINS")
    graph.add_edge("service", "database", "USES")

    print("\nGRAPH STORE")
    print("Service neighbors:", [n.node_id for n in graph.neighbors("repo")])
    print("Path team -> database:", graph.shortest_path("team", "database"))


def validate_edge_cases() -> None:
    document_store = DocumentStore()

    try:
        document_store.insert("", {"name": "invalid"})
    except ValidationError as exc:
        print("\nVALIDATION:", exc)

    key_store = KeyValueStore()
    try:
        key_store.set("bad-ttl", "value", ttl_seconds=0)
    except ValidationError as exc:
        print("VALIDATION:", exc)

    graph = GraphStore()
    graph.add_node("a", ["Node"])
    try:
        graph.add_edge("a", "missing", "LINKS")
    except NotFoundError as exc:
        print("VALIDATION:", exc)


def main() -> None:
    print("NoSQL Data-Model Case Study")
    print("============================")
    demonstrate_document_store()
    demonstrate_key_value_store()
    demonstrate_column_store()
    demonstrate_graph_store()
    validate_edge_cases()

    print("\nMODEL SELECTION")
    print("Document   -> flexible aggregate-oriented records")
    print("Key-value  -> direct lookup, caching, sessions")
    print("Column     -> sparse high-volume row/column workloads")
    print("Graph      -> relationship traversal and connected data")


if __name__ == "__main__":
    main()
