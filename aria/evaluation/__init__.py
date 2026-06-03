"""ARIA evaluation module.

Provides metrics computation, LLM-as-judge evaluation, and benchmark
runner.  Heavy dependencies (networkx, sentence-transformers, sklearn)
are imported lazily so that ``import aria.evaluation`` never fails at
the package level.
"""


def __getattr__(name):
    """Lazy imports for evaluation submodules."""
    if name == "MetricsComputer":
        from aria.evaluation.metrics import MetricsComputer
        return MetricsComputer
    elif name == "LLMJudge":
        from aria.evaluation.judge import LLMJudge
        return LLMJudge
    elif name == "create_judge_report":
        from aria.evaluation.judge import create_judge_report
        return create_judge_report
    elif name == "BenchmarkRunner":
        from aria.evaluation.benchmark import BenchmarkRunner
        return BenchmarkRunner
    raise AttributeError(f"module 'aria.evaluation' has no attribute {name!r}")


__all__ = [
    "MetricsComputer",
    "LLMJudge",
    "create_judge_report",
    "BenchmarkRunner",
]