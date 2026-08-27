"""Pure graph logic (blueprint section 11.6): checked in isolation, no DB
needed, so a subtle bug here can't silently corrupt the concept graph.
"""

import uuid


def would_create_cycle(
    existing_edges: list[tuple[uuid.UUID, uuid.UUID]], source_id: uuid.UUID, target_id: uuid.UUID
) -> bool:
    """True if adding source_id -> target_id would close a cycle, i.e.
    target_id can already reach source_id via existing_edges (or they're
    the same node)."""
    if source_id == target_id:
        return True

    adjacency: dict[uuid.UUID, list[uuid.UUID]] = {}
    for src, tgt in existing_edges:
        adjacency.setdefault(src, []).append(tgt)

    visited: set[uuid.UUID] = set()
    stack = [target_id]
    while stack:
        node = stack.pop()
        if node == source_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(adjacency.get(node, []))
    return False
