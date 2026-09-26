
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.documents.models import Document, DocumentType


@dataclass
class ContractCluster:
    root_id: str
    document_ids: list[str] = field(default_factory=list)


def build_relationship_graph(documents: list[Document]) -> dict[str, set[str]]:
    """Build an undirected graph from explicit IDs found in document text.

    This is intentionally conservative: an ID mention creates an edge only
    when the referenced document is present in the dataset. Folder names and
    filenames are not treated as ground truth.
    """
    known = {d.document_id for d in documents}
    graph = {d.document_id: set() for d in documents}

    # Explicit parent contract references are the strongest relation.
    # If the parent document is absent, keep the relation as an external root
    # in a synthetic node so several documents can still form one cluster.
    for doc in documents:
        for ref in doc.parent_contract_ids:
            target = ref if ref in known else f"external:{ref}"
            graph.setdefault(target, set())
            graph[doc.document_id].add(target)
            graph[target].add(doc.document_id)

        # Secondary relation: direct reference to another supplied document.
        for ref in doc.referenced_contract_ids:
            if ref in known and ref != doc.document_id:
                graph[doc.document_id].add(ref)
                graph[ref].add(doc.document_id)

    return graph


def connected_components(graph: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    components: list[set[str]] = []

    for node in graph:
        if node in seen:
            continue

        stack = [node]
        component = set()

        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.add(current)
            stack.extend(graph[current] - seen)

        components.append(component)

    return components


def choose_root(component: set[str], by_id: dict[str, Document]) -> str:
    docs = [by_id[x] for x in component]

    # Prefer an explicit contract over an addendum/agreement.
    contracts = [d for d in docs if d.document_type == DocumentType.CONTRACT]
    if contracts:
        return min(
            contracts,
            key=lambda d: (d.document_date or __import__("datetime").date.max, d.document_id),
        ).document_id

    # Otherwise choose the earliest document in the component.
    return min(
        docs,
        key=lambda d: (d.document_date or __import__("datetime").date.max, d.document_id),
    ).document_id


def resolve_clusters(documents: list[Document]) -> list[ContractCluster]:
    by_id = {d.document_id: d for d in documents}
    graph = build_relationship_graph(documents)

    clusters = []
    for component in connected_components(graph):
        real_component = {x for x in component if x in by_id}
        if not real_component:
            continue

        external_roots = sorted(
            x.removeprefix("external:") for x in component if x.startswith("external:")
        )
        root = external_roots[0] if external_roots else choose_root(real_component, by_id)
        ordered = sorted(
            real_component,
            key=lambda x: (
                by_id[x].document_date or __import__("datetime").date.max,
                x,
            ),
        )
        clusters.append(ContractCluster(root_id=root, document_ids=ordered))

    return sorted(clusters, key=lambda x: x.root_id)
