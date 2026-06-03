"""
PSP path search: find causal pathways in a knowledge graph.

This module unifies the path-search logic that was duplicated across
``aria_core_ollama.py``, ``kg_only.py``, and ``naive_kg_ollama.py``.
The core algorithm is keyword-based node matching followed by
``nx.all_simple_paths`` with a configurable hop cutoff.

Typical usage::

    from aria.kg.graph_store import load_kg
    from aria.retrieval.path_search import find_psp_paths

    graph = load_kg("kg.json")
    paths = find_psp_paths(graph, ["CVD", "temperature"], ["mobility", "conductivity"])
    for p in paths:
        print(" -> ".join(p))
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

import networkx as nx

logger = logging.getLogger(__name__)


def _match_nodes(
    graph: nx.DiGraph,
    keywords: List[str],
) -> Set[str]:
    """Return the set of graph nodes whose labels contain any keyword.

    Matching is case-insensitive and uses substring containment.

    Parameters
    ----------
    graph:
        Directed NetworkX graph.
    keywords:
        Keywords to search for.

    Returns
    -------
    set of str
        Node labels that match at least one keyword.
    """
    if not keywords:
        return set()

    matched: Set[str] = set()
    for node in graph.nodes():
        node_lower = node.lower()
        if any(kw.lower() in node_lower for kw in keywords):
            matched.add(node)
    return matched


def find_psp_paths(
    graph: nx.DiGraph,
    start_keywords: List[str],
    end_keywords: List[str],
    max_hops: int = 4,
    reverse: bool = False,
) -> List[List[str]]:
    """Find causal pathways in a PSP knowledge graph.

    The search proceeds by matching *start_keywords* and *end_keywords*
    against node labels, then enumerating all simple paths between matched
    start/end pairs.

    Parameters
    ----------
    graph:
        Directed PSP knowledge graph (as returned by :func:`aria.kg.graph_store.load_kg`).
    start_keywords:
        Keywords to match against source (start) nodes.
    end_keywords:
        Keywords to match against target (end) nodes.
    max_hops:
        Maximum path length (number of edges).  Passed to
        ``nx.all_simple_paths`` as ``cutoff``.
    reverse:
        If *True*, reverse the graph direction before searching.  This is
        useful for inverse-design queries where you start from property
        keywords and trace back to synthesis parameters.

    Returns
    -------
    list of list of str
        Each inner list is an ordered sequence of node labels forming a
        causal path.  Duplicates are removed.
    """
    search_graph = graph.reverse(copy=True) if reverse else graph

    start_nodes = _match_nodes(search_graph, start_keywords)
    end_nodes = _match_nodes(search_graph, end_keywords)

    if not start_nodes:
        logger.debug("No start nodes matched for keywords %s", start_keywords)
        return []
    if not end_nodes:
        logger.debug("No end nodes matched for keywords %s", end_keywords)
        return []

    seen_paths: Set[str] = set()
    unique_paths: List[List[str]] = []

    for source in sorted(start_nodes):
        for target in sorted(end_nodes):
            if source == target:
                continue
            if not nx.has_path(search_graph, source, target):
                continue
            for path in nx.all_simple_paths(search_graph, source, target, cutoff=max_hops):
                path_key = " -> ".join(path)
                if path_key not in seen_paths:
                    seen_paths.add(path_key)
                    unique_paths.append(list(path))

    logger.debug(
        "Found %d unique paths (%d start x %d end nodes, max_hops=%d, reverse=%s)",
        len(unique_paths), len(start_nodes), len(end_nodes), max_hops, reverse,
    )
    return unique_paths


def extract_mechanisms(
    graph: nx.DiGraph,
    paths: List[List[str]],
) -> List[Dict[str, str]]:
    """Extract mechanism text and metadata from edges along paths.

    Parameters
    ----------
    graph:
        Directed PSP knowledge graph.
    paths:
        List of paths (each a list of node labels).

    Returns
    -------
    list of dict
        One dict per edge across all paths, with keys ``source``,
        ``target``, ``mechanism``, ``affected_property``, ``confidence``.
    """
    mechanisms: List[Dict[str, str]] = []
    for path in paths:
        for i in range(len(path) - 1):
            source, target = path[i], path[i + 1]
            data = graph.get_edge_data(source, target)
            if data is None:
                continue
            mechanisms.append({
                "source": source,
                "target": target,
                "mechanism": data.get("mechanism", ""),
                "affected_property": data.get("affected_property", ""),
                "confidence": data.get("confidence", 1.0),
            })
    return mechanisms


def find_paths_for_query(
    graph: nx.DiGraph,
    query_keywords: List[str],
    direction: str = "forward",
    max_hops: int = 4,
) -> List[List[str]]:
    """Convenience wrapper that picks start/end nodes automatically.

    For ``direction="forward"`` the *query_keywords* are matched against
    synthesis-related (root) nodes, and property-related (leaf) nodes are
    used as targets.  For ``direction="inverse"`` the roles are swapped.

    Parameters
    ----------
    graph:
        Directed PSP knowledge graph.
    query_keywords:
        Keywords extracted from the user query.
    direction:
        ``"forward"`` (synthesis -> property) or ``"inverse"``
        (property -> synthesis).
    max_hops:
        Maximum path length.

    Returns
    -------
    list of list of str
        Unique causal paths.
    """
    root_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]

    root_keywords = list({kw for n in root_nodes for kw in n.split()})
    leaf_keywords = list({kw for n in leaf_nodes for kw in n.split()})

    if direction == "forward":
        return find_psp_paths(graph, query_keywords, leaf_keywords, max_hops=max_hops)
    else:
        return find_psp_paths(
            graph,
            root_keywords,
            query_keywords,
            max_hops=max_hops,
            reverse=True,
        )