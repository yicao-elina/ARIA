"""
Knowledge-graph quality diagnostics.

Ported from ``26KDD/src/kg_diagnostics.py`` and cleaned up with proper
type hints, logging, and separation of concerns.  The :class:`KGDiagnostics`
class analyses a PSP causal graph for structural quality, content richness,
query coverage, semantic diversity, and data-gap estimates.

Typical usage::

    from aria.kg.diagnostics import KGDiagnostics

    diag = KGDiagnostics("path/to/kg.json")
    report = diag.generate_report()
    diag.print_report(report)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from aria.kg.graph_store import load_kg

logger = logging.getLogger(__name__)


class KGDiagnostics:
    """Comprehensive KG quality analysis.

    Parameters
    ----------
    kg_source:
        Either a file path (``str`` or ``Path``) to an enriched JSON, or
        a pre-loaded :class:`networkx.DiGraph`.
    """

    def __init__(self, kg_source: str | Path | nx.DiGraph) -> None:
        if isinstance(kg_source, nx.DiGraph):
            self.kg: nx.DiGraph = kg_source
            self.kg_file: Optional[Path] = None
        else:
            self.kg_file = Path(kg_source)
            self.kg = load_kg(str(self.kg_file))

        self._embedding_model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Lazy embedding model
    # ------------------------------------------------------------------

    def _get_embedding_model(self):
        """Lazily load SentenceTransformer for diversity analysis."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model for diversity analysis …")
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedding_model

    # ------------------------------------------------------------------
    # Structure
    # ------------------------------------------------------------------

    def analyze_structure(self) -> Dict[str, Any]:
        """Analyse graph structure metrics.

        Returns node/edge counts, density, degree statistics, DAG check,
        connected component counts, longest path length, and samples of
        root / leaf / intermediate nodes.
        """
        logger.info("Analysing graph structure …")
        G = self.kg

        num_nodes = G.number_of_nodes()
        num_edges = G.number_of_edges()
        density = nx.density(G)

        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())
        total_degrees = dict(G.degree())

        root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
        leaf_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
        intermediate_nodes = [n for n in G.nodes() if G.in_degree(n) > 0 and G.out_degree(n) > 0]

        is_dag = nx.is_directed_acyclic_graph(G)
        weakly_connected = nx.number_weakly_connected_components(G)
        strongly_connected = nx.number_strongly_connected_components(G)

        try:
            longest_path_length = len(nx.dag_longest_path(G)) if is_dag else 0
        except Exception:
            longest_path_length = 0

        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "density": float(density),
            "avg_in_degree": float(np.mean(list(in_degrees.values()))) if in_degrees else 0.0,
            "avg_out_degree": float(np.mean(list(out_degrees.values()))) if out_degrees else 0.0,
            "avg_degree": float(np.mean(list(total_degrees.values()))) if total_degrees else 0.0,
            "max_in_degree": max(in_degrees.values()) if in_degrees else 0,
            "max_out_degree": max(out_degrees.values()) if out_degrees else 0,
            "num_root_nodes": len(root_nodes),
            "num_leaf_nodes": len(leaf_nodes),
            "num_intermediate_nodes": len(intermediate_nodes),
            "is_dag": is_dag,
            "weakly_connected_components": weakly_connected,
            "strongly_connected_components": strongly_connected,
            "longest_path_length": longest_path_length,
            "root_nodes": root_nodes[:10],
            "leaf_nodes": leaf_nodes[:10],
        }

    # ------------------------------------------------------------------
    # Content quality
    # ------------------------------------------------------------------

    def analyze_content(self) -> Dict[str, Any]:
        """Analyse content quality metrics.

        Evaluates mechanism coverage, property annotation coverage,
        average confidence, and unique affected-property counts.
        """
        logger.info("Analysing content quality …")
        G = self.kg

        edges_with_mechanism = 0
        edges_without_mechanism = 0
        mechanism_lengths: list[int] = []

        for _u, _v, data in G.edges(data=True):
            mechanism = data.get("mechanism", "")
            if mechanism and mechanism.strip():
                edges_with_mechanism += 1
                mechanism_lengths.append(len(mechanism))
            else:
                edges_without_mechanism += 1

        total_edges = G.number_of_edges()
        mechanism_coverage = edges_with_mechanism / total_edges if total_edges else 0.0

        edges_with_property = sum(1 for _u, _v, d in G.edges(data=True) if d.get("affected_property"))
        property_coverage = edges_with_property / total_edges if total_edges else 0.0

        confidences = [d.get("confidence", 1.0) for _u, _v, d in G.edges(data=True)]
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0

        unique_properties = {
            d.get("affected_property", "")
            for _u, _v, d in G.edges(data=True)
            if d.get("affected_property")
        }

        return {
            "mechanism_coverage": float(mechanism_coverage),
            "edges_with_mechanism": edges_with_mechanism,
            "edges_without_mechanism": edges_without_mechanism,
            "avg_mechanism_length": float(np.mean(mechanism_lengths)) if mechanism_lengths else 0.0,
            "property_coverage": float(property_coverage),
            "edges_with_property": edges_with_property,
            "avg_confidence": float(avg_confidence),
            "num_unique_properties": len(unique_properties),
            "unique_properties": sorted(unique_properties)[:20],
        }

    # ------------------------------------------------------------------
    # Query coverage
    # ------------------------------------------------------------------

    def analyze_coverage(self, test_queries: Optional[list[dict[str, Any]]] = None) -> Dict[str, Any]:
        """Analyse KG coverage for representative queries.

        Parameters
        ----------
        test_queries:
            Optional list of dicts with keys ``type``, ``keywords``, ``target``.
            If *None*, a default set of materials-science queries is used.

        Returns
        -------
        dict
            Coverage statistics including ``coverage_rate`` and per-query details.
        """
        logger.info("Analysing query coverage …")
        G = self.kg

        if test_queries is None:
            test_queries = [
                {"type": "forward", "keywords": ["temperature", "CVD"], "target": ["mobility", "conductivity"]},
                {"type": "forward", "keywords": ["pressure", "doping"], "target": ["carrier", "concentration"]},
                {"type": "forward", "keywords": ["annealing", "oxygen"], "target": ["defect", "property"]},
                {"type": "inverse", "keywords": ["n-type", "high mobility"], "target": ["temperature", "method"]},
                {"type": "inverse", "keywords": ["p-type", "doping"], "target": ["dopant", "concentration"]},
            ]

        total_paths = 0
        queries_with_match = 0
        query_details: list[dict[str, Any]] = []

        for query in test_queries:
            start_nodes = {
                n for n in G.nodes()
                if any(kw.lower() in n.lower() for kw in query["keywords"])
            }
            end_nodes = {
                n for n in G.nodes()
                if any(kw.lower() in n.lower() for kw in query["target"])
            }

            num_paths = 0
            for start in start_nodes:
                for end in end_nodes:
                    if nx.has_path(G, start, end):
                        for _path in nx.all_simple_paths(G, start, end, cutoff=4):
                            num_paths += 1

            total_paths += num_paths
            if num_paths > 0:
                queries_with_match += 1

            query_details.append({
                "type": query["type"],
                "keywords": query["keywords"],
                "target": query["target"],
                "num_paths": num_paths,
                "has_match": num_paths > 0,
            })

        n_queries = len(test_queries)
        coverage_rate = queries_with_match / n_queries if n_queries else 0.0

        return {
            "total_queries": n_queries,
            "queries_with_match": queries_with_match,
            "queries_without_match": n_queries - queries_with_match,
            "avg_paths_per_query": total_paths / n_queries if n_queries else 0.0,
            "coverage_rate": float(coverage_rate),
            "query_details": query_details,
        }

    # ------------------------------------------------------------------
    # Semantic diversity
    # ------------------------------------------------------------------

    def analyze_diversity(self) -> Dict[str, Any]:
        """Analyse semantic diversity of KG nodes using embeddings.

        Requires the ``sentence-transformers`` package.

        Returns
        -------
        dict
            ``diversity_score`` (higher = more diverse), ``avg_similarity``,
            and the most/least similar node pairs.
        """
        logger.info("Analysing semantic diversity …")
        model = self._get_embedding_model()

        nodes = list(self.kg.nodes())
        if len(nodes) < 2:
            return {"diversity_score": 0.0, "avg_similarity": 0.0, "note": "Too few nodes"}

        from sklearn.metrics.pairwise import cosine_similarity as _cosine_sim

        embeddings = model.encode(nodes)
        similarities = _cosine_sim(embeddings)
        np.fill_diagonal(similarities, 0.0)

        avg_similarity = float(np.mean(similarities))
        diversity_score = 1.0 - avg_similarity

        # Collect unique pairs
        similar_pairs: list[tuple[str, str, float]] = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                similar_pairs.append((nodes[i], nodes[j], float(similarities[i][j])))

        similar_pairs.sort(key=lambda p: p[2], reverse=True)

        return {
            "diversity_score": float(diversity_score),
            "avg_similarity": float(avg_similarity),
            "most_similar_pairs": [(p[0], p[1], p[2]) for p in similar_pairs[:5]],
            "least_similar_pairs": [(p[0], p[1], p[2]) for p in similar_pairs[-5:]],
        }

    # ------------------------------------------------------------------
    # Gap estimation
    # ------------------------------------------------------------------

    def estimate_kg_gaps(
        self,
        structure: Optional[Dict[str, Any]] = None,
        coverage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Estimate how many edges / papers are needed to improve KG coverage.

        Parameters
        ----------
        structure:
            Output of :meth:`analyze_structure`.  If *None*, it is computed.
        coverage:
            Output of :meth:`analyze_coverage`.  If *None*, it is computed.

        Returns
        -------
        dict
            Gap estimates keyed by target coverage percentage, plus a
            human-readable ``recommendation`` string.
        """
        logger.info("Estimating KG gaps …")

        if structure is None:
            structure = self.analyze_structure()
        if coverage is None:
            coverage = self.analyze_coverage()

        current_edges = structure["num_edges"]
        coverage_rate = coverage["coverage_rate"]

        estimates: Dict[str, Any] = {}
        for target_pct in (50, 70, 90):
            target_coverage = target_pct / 100.0
            key = f"{target_pct}%_coverage"
            if coverage_rate > 0:
                needed_edges = int(current_edges * (target_coverage / coverage_rate))
                additional = max(0, needed_edges - current_edges)
                estimates[key] = {"target_edges": needed_edges, "additional_edges_needed": additional}
            else:
                estimates[key] = {"target_edges": "unknown", "additional_edges_needed": "unknown (coverage = 0)"}

        # Estimate papers needed (2-5 edges per paper)
        papers_needed: Dict[str, Any] = {}
        for target, data in estimates.items():
            additional = data.get("additional_edges_needed")
            if isinstance(additional, int):
                papers_needed[target] = {"min_papers": additional // 5, "max_papers": additional // 2}
            else:
                papers_needed[target] = "unknown"

        return {
            "current_coverage": float(coverage_rate),
            "coverage_estimates": estimates,
            "papers_needed_estimates": papers_needed,
            "recommendation": self._get_recommendation(structure, coverage),
        }

    @staticmethod
    def _get_recommendation(structure: Dict[str, Any], coverage: Dict[str, Any]) -> str:
        """Generate a human-readable recommendation from stats."""
        edges = structure["num_edges"]
        coverage_rate = coverage.get("coverage_rate", 0)

        if edges < 50:
            return "CRITICAL: KG too small (<50 edges). Need 100-500 edges for meaningful evaluation."
        if edges < 100:
            return "LOW: KG small (50-100 edges). Recommend enrichment to 200+ edges."
        if coverage_rate < 0.3:
            return "MODERATE: Decent size but low coverage. Focus on improving coverage of common queries."
        if coverage_rate < 0.5:
            return "GOOD: Good size and coverage. Can proceed with testing. Enrichment will improve results."
        return "EXCELLENT: High coverage. Proceed with testing confidently."

    # ------------------------------------------------------------------
    # Full report
    # ------------------------------------------------------------------

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive KG quality report.

        Returns a dict with keys ``structure``, ``content``, ``coverage``,
        ``diversity``, and ``gaps``.
        """
        logger.info("Generating comprehensive report …")

        structure = self.analyze_structure()
        content = self.analyze_content()
        coverage = self.analyze_coverage()
        diversity = self.analyze_diversity()

        gaps = self.estimate_kg_gaps(structure, coverage)

        return {
            "kg_file": str(self.kg_file) if self.kg_file else "<in-memory graph>",
            "structure": structure,
            "content": content,
            "coverage": coverage,
            "diversity": diversity,
            "gaps": gaps,
        }

    # ------------------------------------------------------------------
    # Pretty-print
    # ------------------------------------------------------------------

    @staticmethod
    def print_report(report: Dict[str, Any]) -> None:
        """Print a formatted KG quality report to stdout."""
        print("\n" + "=" * 70)
        print("KNOWLEDGE GRAPH QUALITY DIAGNOSTIC REPORT")
        print("=" * 70)
        print(f"\nKG File: {report['kg_file']}")

        s = report["structure"]
        print("\n" + "-" * 70)
        print("1. GRAPH STRUCTURE")
        print("-" * 70)
        print(f"  Nodes:                 {s['num_nodes']}")
        print(f"  Edges:                 {s['num_edges']}")
        print(f"  Density:               {s['density']:.4f}")
        print(f"  Avg Degree:            {s['avg_degree']:.2f}")
        print(f"  Root Nodes:            {s['num_root_nodes']} (synthesis parameters)")
        print(f"  Leaf Nodes:            {s['num_leaf_nodes']} (properties)")
        print(f"  Intermediate Nodes:    {s['num_intermediate_nodes']}")
        print(f"  Is DAG:                {s['is_dag']}")
        print(f"  Longest Path:          {s['longest_path_length']} hops")
        print(f"  Weakly Connected:      {s['weakly_connected_components']} component(s)")

        c = report["content"]
        print("\n" + "-" * 70)
        print("2. CONTENT QUALITY")
        print("-" * 70)
        total_edges = c["edges_with_mechanism"] + c["edges_without_mechanism"]
        print(f"  Mechanism Coverage:    {c['mechanism_coverage']:.1%} ({c['edges_with_mechanism']}/{total_edges})")
        print(f"  Avg Mechanism Length:  {c['avg_mechanism_length']:.0f} chars")
        print(f"  Property Coverage:     {c['property_coverage']:.1%}")
        print(f"  Avg Confidence:        {c['avg_confidence']:.2f}")
        print(f"  Unique Properties:     {c['num_unique_properties']}")

        cov = report["coverage"]
        print("\n" + "-" * 70)
        print("3. QUERY COVERAGE")
        print("-" * 70)
        print(f"  Test Queries:          {cov['total_queries']}")
        print(f"  Queries with Match:     {cov['queries_with_match']} ({cov['coverage_rate']:.1%})")
        print(f"  Queries without Match: {cov['queries_without_match']}")
        print(f"  Avg Paths per Query:   {cov['avg_paths_per_query']:.1f}")

        d = report["diversity"]
        print("\n" + "-" * 70)
        print("4. SEMANTIC DIVERSITY")
        print("-" * 70)
        print(f"  Diversity Score:       {d['diversity_score']:.3f} (higher = more diverse)")
        print(f"  Avg Node Similarity:   {d['avg_similarity']:.3f} (lower = more diverse)")

        g = report["gaps"]
        print("\n" + "-" * 70)
        print("5. KG GAPS & RECOMMENDATIONS")
        print("-" * 70)
        print(f"  Current Coverage:      {g['current_coverage']:.1%}")
        for pct in ("50%", "70%", "90%"):
            key = f"{pct}_coverage"
            est = g["coverage_estimates"].get(key, {})
            addl = est.get("additional_edges_needed", "unknown")
            print(f"\n  To achieve {pct} coverage:")
            if isinstance(addl, int):
                print(f"    Additional edges:    {addl}")
                pneed = g["papers_needed_estimates"].get(key, "unknown")
                if isinstance(pneed, dict):
                    print(f"    Papers needed:       {pneed['min_papers']}-{pneed['max_papers']}")
            else:
                print(f"    {addl}")
        print(f"\n  RECOMMENDATION: {g['recommendation']}")
        print("\n" + "=" * 70)

    # ------------------------------------------------------------------
    # Save report
    # ------------------------------------------------------------------

    @staticmethod
    def save_report(report: Dict[str, Any], output_file: str = "kg_quality_report.json") -> None:
        """Save a report dict to JSON, converting numpy types automatically."""
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)

        def _convert(obj: Any) -> Any:
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(i) for i in obj]
            if isinstance(obj, tuple):
                return tuple(_convert(i) for i in obj)
            return obj

        clean = _convert(report)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(clean, fh, indent=2, ensure_ascii=False)
        logger.info("Report saved to %s", out)