"""
Unit tests for Chronos-ASIL Benchmark & Evaluation Harness.
"""

from src.eval.benchmark import ChronosBenchmarkHarness


def test_benchmark_execution():
    harness = ChronosBenchmarkHarness()
    results = harness.run_benchmark()

    assert results["total_test_cases"] == 4
    assert results["mathematical_contradictions_detected"] == 2
    assert results["formal_groundedness_score"] == 1.0
    assert results["hallucination_rate"] == 0.0
    assert results["average_solver_latency_ms"] < 200.0  # Z3 is sub-second fast
