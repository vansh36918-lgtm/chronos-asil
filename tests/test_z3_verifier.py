"""
Unit tests for Microsoft Z3 SMT Formal Safety Verifier.
"""

import pytest
from src.core.models import RequirementItem, ASILRating, Z3ProofStatus
from src.formal.z3_verifier import Z3SafetyVerifier


def test_z3_proves_contradiction_on_cold_crank_latency():
    """Tests that Z3 mathematically proves a contradiction when cold-crank conflicts with latency."""
    verifier = Z3SafetyVerifier()

    contradictory_req = RequirementItem(
        req_id="TEST-UNSAT-01",
        subsystem="Matrix_Headlamp_Driver",
        description="Must switch high beam in 40ms during cold-crank 6.0V.",
        asil_level=ASILRating.ASIL_D,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=6.0,
        t_response_max_ms=40.0,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )

    result = verifier.verify_requirement_consistency(contradictory_req)
    assert result.status == Z3ProofStatus.PROVEN_CONTRADICTION
    assert "UNSAT" in result.theorem_statement
    assert "Cold Crank Active" in result.counterexample["condition"]


def test_z3_verifies_satisfiable_nominal_spec():
    """Tests that Z3 validates achievable specifications as SATISFIABLE."""
    verifier = Z3SafetyVerifier()

    valid_req = RequirementItem(
        req_id="TEST-SAT-02",
        subsystem="77GHz_Radar",
        description="Radar telemetry transmission within 250ms at 12V nominal.",
        asil_level=ASILRating.ASIL_B,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=8.0,
        t_response_max_ms=250.0,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )

    result = verifier.verify_requirement_consistency(valid_req)
    assert result.status == Z3ProofStatus.SATISFIABLE


def test_z3_mutual_exclusion():
    """Tests mutual exclusion detection between conflicting voltage envelopes."""
    verifier = Z3SafetyVerifier()

    req_a = RequirementItem(
        req_id="REQ-A",
        subsystem="Subsystem_A",
        description="Voltage 10-12V",
        v_operating_min=10.0,
        v_operating_max=12.0
    )
    req_b = RequirementItem(
        req_id="REQ-B",
        subsystem="Subsystem_B",
        description="Voltage 13-16V",
        v_operating_min=13.0,
        v_operating_max=16.0
    )

    is_conflict, explanation = verifier.verify_mutual_exclusion(req_a, req_b)
    assert is_conflict is True
    assert "MUTUALLY EXCLUSIVE CONFLICT" in explanation
