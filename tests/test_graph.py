"""
Unit tests for LangGraph Stateful Workflow & Human-in-the-Loop Interruption.
"""

from src.core.models import RequirementItem, ASILRating
from src.agent.graph import create_chronos_workflow


def test_langgraph_hitl_breakpoint_and_resumption():
    """
    Tests that:
    1. LangGraph runs up to the human_in_the_loop_gate breakpoint when Z3 proves a contradiction.
    2. Execution pauses and state is saved in MemorySaver checkpointer.
    3. Human injects approval/override.
    4. Execution resumes to completion and produces the ASPICE certificate.
    """
    workflow = create_chronos_workflow()
    config = {"configurable": {"thread_id": "test_thread_001"}}

    # Contradictory requirement (Cold-crank 6.0V with 40ms response - physically impossible)
    req = RequirementItem(
        req_id="REQ-TEST-UNSAT",
        subsystem="Matrix_Headlamp",
        description="Cold-crank 6.0V with 40ms latency",
        asil_level=ASILRating.ASIL_D,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=6.0,
        t_response_max_ms=40.0,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )

    initial_state = {
        "raw_spec_text": "Sample Test Spec",
        "requirements": [req],
        "audit_trail": [],
        "human_approved": False,
        "human_feedback": None,
        "human_signed_by": None
    }

    # Execute until breakpoint
    _ = list(workflow.stream(initial_state, config))

    # Verify execution paused at breakpoint
    state_at_breakpoint = workflow.get_state(config)
    assert state_at_breakpoint.next == ("human_in_the_loop_gate",)
    assert state_at_breakpoint.values.get("has_safety_contradiction") is True

    # Simulate Human Engineer Review & Sign-off
    workflow.update_state(
        config,
        {
            "human_approved": True,
            "human_feedback": "Approved with charge-pump hardware revision #104.",
            "human_signed_by": "Vansh (Senior Automotive Safety Lead)"
        }
    )

    # Resume execution
    resume_events = list(workflow.stream(None, config))
    assert len(resume_events) > 0

    # Verify final completion and ASPICE certificate
    final_state = workflow.get_state(config)
    assert len(final_state.next) == 0  # Finished!
    cert = final_state.values.get("aspice_certificate")
    assert cert is not None
    assert cert.asil_d_compliance_status == "COMPLIANT_ASIL_D"
    assert cert.human_in_the_loop_approver == "Vansh (Senior Automotive Safety Lead)"


def test_langgraph_nominal_satisfiable_execution():
    """Tests that a valid requirement without contradictions executes cleanly."""
    workflow = create_chronos_workflow()
    config = {"configurable": {"thread_id": "test_thread_002"}}

    req = RequirementItem(
        req_id="REQ-NOMINAL-01",
        subsystem="Cabin_Lighting",
        description="Nominal operation",
        asil_level=ASILRating.QM,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=8.0,
        t_response_max_ms=300.0,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )

    initial_state = {
        "raw_spec_text": "Nominal Spec",
        "requirements": [req],
        "audit_trail": [],
        "human_approved": False
    }

    _ = list(workflow.stream(initial_state, config))
    final_state = workflow.get_state(config)

    # Nominal route doesn't require human interrupt
    assert final_state.values.get("has_safety_contradiction") is False
    assert final_state.values.get("aspice_certificate") is not None
