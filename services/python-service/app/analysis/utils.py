from collections.abc import Iterator


def iter_nodes(node) -> Iterator:
    yield node
    for child in node.children:
        yield from iter_nodes(child)


def node_text(node, source: str) -> str:
    return source.encode("utf-8")[node.start_byte : node.end_byte].decode("utf-8")


def node_line(node) -> int:
    return node.start_point[0] + 1


def node_end_line(node) -> int:
    return node.end_point[0] + 1


def child_text(node, field_name: str, source: str) -> str | None:
    child = node.child_by_field_name(field_name)
    return node_text(child, source) if child is not None else None
