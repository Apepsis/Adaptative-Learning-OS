import uuid

from app.modules.curriculum.graph import would_create_cycle


def test_no_cycle_on_an_empty_graph() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    assert would_create_cycle([], a, b) is False


def test_self_loop_is_always_a_cycle() -> None:
    a = uuid.uuid4()
    assert would_create_cycle([], a, a) is True


def test_closing_a_chain_into_a_loop_is_detected() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    edges = [(a, b), (b, c)]
    assert would_create_cycle(edges, c, a) is True


def test_a_shortcut_edge_is_not_a_cycle() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    edges = [(a, b), (b, c)]
    assert would_create_cycle(edges, a, c) is False


def test_unrelated_node_does_not_trigger_a_false_positive() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    unrelated = uuid.uuid4()
    edges = [(a, b)]
    assert would_create_cycle(edges, unrelated, a) is False


def test_long_chain_cycle_is_still_detected() -> None:
    nodes = [uuid.uuid4() for _ in range(6)]
    edges = list(zip(nodes, nodes[1:], strict=False))  # n0->n1->n2->...->n5
    assert would_create_cycle(edges, nodes[-1], nodes[0]) is True
