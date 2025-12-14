from __future__ import annotations

from pathlib import Path

import networkx as nx
from pyvis.network import Network


def export_pyvis(g: nx.DiGraph, out: Path, height: str = "800px") -> Path:
    net = Network(height=height, width="100%", directed=True)
    net.from_nx(g)
    out.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(out))
    return out
