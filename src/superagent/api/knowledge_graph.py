from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends

from superagent.api.chat import get_container
from superagent.application.container import AppContainer

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


@router.get("")
def get_knowledge_graph(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Return a deterministic graph derived from persisted knowledge.

    The first implementation deliberately avoids inventing semantic edges. It
    exposes real document/chunk/knowledge relationships already present in the
    database so the UI can render useful data even before semantic graph
    extraction is enabled.
    """
    documents = list(container.document_repository.list_documents())
    knowledge = list(container.knowledge_repository.list_knowledge())
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()

    def add_node(node_id: str, label: str, group: str, **extra: Any) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append({"id": node_id, "label": label, "group": group, **extra})

    for document in documents:
        add_node(document.document_id, document.title, "document", document_type=document.document_type)
        for chunk in document.chunks:
            add_node(chunk.chunk_id, f"Chunk {chunk.chunk_index + 1}", "chunk", document_id=document.document_id)
            edges.append({"id": f"doc-chunk:{document.document_id}:{chunk.chunk_id}", "source": document.document_id, "target": chunk.chunk_id, "relation": "contains"})

    for item in knowledge:
        add_node(item.knowledge_id, item.title or item.kind, "knowledge", kind=item.kind)
        if item.document_id:
            add_node(item.document_id, item.document_id, "document")
            edges.append({"id": f"document-knowledge:{item.document_id}:{item.knowledge_id}", "source": item.document_id, "target": item.knowledge_id, "relation": "supports"})
        if item.chunk_id:
            add_node(item.chunk_id, item.chunk_id, "chunk")
            edges.append({"id": f"chunk-knowledge:{item.chunk_id}:{item.knowledge_id}", "source": item.chunk_id, "target": item.knowledge_id, "relation": "derived_from"})

    return {"nodes": nodes, "edges": edges, "stats": {"documents": len(documents), "knowledge": len(knowledge), "nodes": len(nodes), "edges": len(edges)}}
