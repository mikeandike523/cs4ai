from dataclasses import dataclass, field
from typing import List, Dict, Iterable, Callable, Tuple, Union

PathLike = Union[str, Iterable[str]]

@dataclass
class Node:
    name: str
    children: Dict[str, "Node"] = field(default_factory=dict)
    # Whether at least one input path ends exactly at this node
    terminal: bool = False

    def add(self, segments: List[str]):
        if not segments:
            self.terminal = True
            return
        head, *tail = segments
        child = self.children.get(head)
        if child is None:
            child = self.children[head] = Node(head)
        child.add(tail)

def default_split(
    p: PathLike, delimiter: str = "/"
) -> Tuple[str, List[str]]:
    """
    Returns (root_label, segments_without_root).

    Rules:
    - If p is a string and starts with delimiter => absolute: root_label = delimiter.
    - Else => relative: root_label = first token.
    - If p is an iterable of tokens, we consider absolute iff first token == delimiter.
    """
    if isinstance(p, str):
        if not p:
            return ("", [])  # empty path becomes empty root; adjust if you want to drop it
        if p.startswith(delimiter):
            # absolute: root is the delimiter itself; strip *one* leading delimiter
            body = p[len(delimiter):]
            segs = [s for s in body.split(delimiter) if s]
            return (delimiter, segs)
        else:
            segs = [s for s in p.split(delimiter) if s]
            if not segs:
                return ("", [])
            return (segs[0], segs[1:])
    else:
        # iterable of tokens
        tokens = list(p)
        if not tokens:
            return ("", [])
        if tokens[0] == delimiter:
            return (delimiter, tokens[1:])
        return (tokens[0], tokens[1:])

def paths_to_forest(
    paths: List[PathLike],
    *,
    splitter: Callable[[PathLike], Tuple[str, List[str]]] = None,
    delimiter: str = "/"
) -> List[Node]:
    """
    Build a forest (list of root Nodes). Roots are determined by the splitter’s
    root_label. All nodes are pure token-based (no filesystem calls).
    """
    if splitter is None:
        splitter = lambda p: default_split(p, delimiter=delimiter)

    # Group by root_label
    roots: Dict[str, Node] = {}

    for p in paths:
        root_label, segs = splitter(p)
        if root_label not in roots:
            roots[root_label] = Node(root_label or "<root>")  # name tweak for empty root
        roots[root_label].add(segs)

    # Return a stable list (sorted by root name); drop if you prefer insertion order
    return [roots[k] for k in sorted(roots.keys())]

# ---- Pretty printer for debugging
def render(node: Node, indent: int = 4) -> str:
    """Render a Node tree with a colon after nodes that have children."""
    lines: list[str] = []

    def recursion(n: Node, depth: int):
        prefix = " " * (depth * indent)
        suffix = ":" if n.children else ""
        lines.append(f"{prefix}{n.name}{suffix}")
        for name in sorted(n.children.keys()):
            recursion(n.children[name], depth + 1)

    recursion(node, 0)
    return "\n".join(lines)