"""Causal graph builder and DOT exporter for the BSides demo.

After each run, produces a `causal_graph.dot` file showing exactly
which data influenced which decision, with trust labels on every edge.
Renderable with Graphviz: `dot -Tsvg causal_graph.dot -o causal_graph.svg`
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GraphNode:
    id: str
    label: str
    # file / agent / memory / data / tool / decision
    node_type: str
    trust: str = "untrusted"
    compromised: bool = False


@dataclass
class GraphEdge:
    src: str
    dst: str
    label: str = ""
    tainted: bool = False


# DOT shape per node type
_SHAPE: dict = {
    "file":     "note",
    "agent":    "box",
    "memory":   "cylinder",
    "data":     "ellipse",
    "tool":     "component",
    "decision": "diamond",
}


class CausalGraph:
    """Directed causal graph suitable for exporting to Graphviz DOT format."""

    def __init__(self) -> None:
        self._nodes: List[GraphNode] = []
        self._edges: List[GraphEdge] = []
        self._node_ids: set = set()

    def add_node(self, node: GraphNode) -> None:
        if node.id not in self._node_ids:
            self._nodes.append(node)
            self._node_ids.add(node.id)

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)

    # ------------------------------------------------------------------

    def to_dot(self) -> str:
        lines = [
            "digraph causal_graph {",
            '  graph [rankdir=LR, fontname="Helvetica", bgcolor=white, '
            'label="BSides Demo — Attack Causal Graph", labelloc=t, fontsize=14];',
            '  node [fontname="Helvetica", style=filled, fontsize=11];',
            '  edge [fontname="Helvetica", fontsize=10];',
            "",
        ]

        for node in self._nodes:
            shape = _SHAPE.get(node.node_type, "box")
            if node.compromised:
                fill = "tomato"
                font_suffix = "-Bold"
            elif node.trust == "trusted":
                fill = "lightgreen"
                font_suffix = ""
            else:
                fill = "lightyellow"
                font_suffix = ""
            label = node.label.replace('"', '\\"')
            lines.append(
                f'  "{node.id}" [label="{label}", shape={shape}, '
                f'fillcolor={fill}, fontname="Helvetica{font_suffix}"];'
            )

        lines.append("")

        for edge in self._edges:
            color = "red" if edge.tainted else "black"
            style = "dashed" if edge.tainted else "solid"
            lw = "2.0" if edge.tainted else "1.0"
            label = edge.label.replace('"', '\\"')
            lines.append(
                f'  "{edge.src}" -> "{edge.dst}" '
                f'[label="{label}", color={color}, style={style}, penwidth={lw}];'
            )

        # Legend subgraph
        lines.extend(
            [
                "",
                "  subgraph cluster_legend {",
                '    label="Legend"; style=dashed; fontsize=10; color=gray;',
                '    L1 [label="Compromised", shape=box, fillcolor=tomato, style=filled, fontsize=9];',
                '    L2 [label="Trusted", shape=box, fillcolor=lightgreen, style=filled, fontsize=9];',
                '    L3 [label="Untrusted", shape=box, fillcolor=lightyellow, style=filled, fontsize=9];',
                '    L4 [label="Tainted edge", shape=plaintext, fontcolor=red, fontsize=9];',
                "    { rank=same; L1; L2; L3; L4; }",
                "  }",
                "}",
            ]
        )

        return "\n".join(lines) + "\n"

    def write(self, path: str) -> None:
        """Write the DOT source to `path`."""
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_dot())

    def try_render_svg(self, dot_path: str) -> Optional[str]:
        """Render an SVG using the `dot` CLI if Graphviz is installed.

        Returns the SVG file path on success, or None if Graphviz is not
        available or rendering fails.
        """
        svg_path = dot_path.rsplit(".dot", 1)[0] + ".svg"
        try:
            result = subprocess.run(
                ["dot", "-Tsvg", dot_path, "-o", svg_path],
                capture_output=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and os.path.exists(svg_path):
                return svg_path
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return None
