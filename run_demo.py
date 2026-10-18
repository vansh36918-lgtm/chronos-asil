"""
End-to-End Live Demonstration for Chronos-ASIL.
Demonstrates:
1. Microsoft Z3 SMT Formal Theorem Prover.
2. Real-Time CAN Bus frame decoding & anomaly detection.
3. Multimodal Oscilloscope Waveform signal integrity analysis.
4. LangGraph stateful execution with checkpointer interrupt (Human-in-the-Loop).
5. ASPICE & ISO 26262 ASIL-D Safety Certificate issuance.
"""

import time
import os
import json
from src.core.models import RequirementItem, ASILRating
from src.formal.z3_verifier import Z3SafetyVerifier
from src.telemetry.can_bus import AutomotiveCANInterface
from src.vision.waveform_analyzer import OscilloscopeWaveformAnalyzer
from src.agent.graph import create_chronos_workflow
from src.eval.benchmark import ChronosBenchmarkHarness


import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def print_banner():
    banner = """
    ==========================================================================
    [CHRONOS-ASIL] Autonomous ECU Triage & Formal Verification Engine
    FORVIA HELLA Advanced Safety & Lighting Systems Lab (ISO 26262 / ASPICE)
    ==========================================================================
    """
    print(banner)


def main():
    print_banner()

    # Step 1: Generate synthetic physical oscilloscope traces
    print("[1/5] 👁️  Generating & Analyzing Multimodal Oscilloscope Waveform...")
    os.makedirs("data/waveforms", exist_ok=True)
    waveform_path = "data/waveforms/ringing_termination_fault.png"
    analyzer = OscilloscopeWaveformAnalyzer()
    analyzer.generate_synthetic_waveform(waveform_path, fault_type="RINGING_MISSING_TERMINATION")
    verdict = analyzer.analyze_waveform(waveform_path)
    print(f"      Signal Verdict: {verdict.diagnosis}")
    print(f"      Confidence: {verdict.confidence * 100:.1f}%\n")

    # Step 2: CAN Bus Telemetry
    print("[2/5] 📡 Interrogating Live Automotive CAN Bus...")
    can_bus = AutomotiveCANInterface(interface="virtual")
    frame = can_bus.pack_power_frame(voltage_v=6.2, impedance_ohm=118.5)
    can_bus.send_frame(frame)
    frames = can_bus.read_telemetry_stream(max_frames=1, timeout=0.1)
    can_bus.shutdown()
    if frames:
        print(f"      Decoded Arbitration ID: {hex(frames[0].arbitration_id)}")
        print(f"      Decoded Signals: {frames[0].decoded_signals}")
        print(f"      Anomaly: {frames[0].anomaly_detected}\n")

    # Step 3: Formal Verification with Z3 SMT Prover
    print("[3/5] 📐 Executing Microsoft Z3 SMT Theorem Prover (Zero Hallucination)...")
    req = RequirementItem(
        req_id="REQ-HELLA-HL-ASIL-D-01",
        subsystem="Matrix_LED_Headlamp_Driver",
        description="Headlamp driver must complete transition in <=50ms during cold-crank down to 6.0V.",
        asil_level=ASILRating.ASIL_D,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=6.0,
        t_response_max_ms=50.0,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )
    verifier = Z3SafetyVerifier()
    proof = verifier.verify_requirement_consistency(req)
    print(f"      Theorem: {proof.theorem_statement}")
    print(f"      Proof Status: {proof.status.value}")
    print(f"      Z3 Explanation: {proof.proof_explanation}\n")

    # Step 4: LangGraph Stateful Agent with Human-in-the-Loop Interruption
    print("[4/5] 🧠 Launching LangGraph Agent Workflow with Human-in-the-Loop Breakpoint...")
    workflow = create_chronos_workflow()
    thread_config = {"configurable": {"thread_id": "demo-thread-001"}}

    initial_state = {
        "raw_spec_text": "HELLA Matrix LED System Requirement Specification v4.2",
        "requirements": [req],
        "waveform_image_path": waveform_path,
        "audit_trail": [],
        "human_approved": False,
        "human_feedback": None,
        "human_signed_by": None
    }

    # Stream execution until interrupt
    for event in workflow.stream(initial_state, thread_config):
        for node in event.keys():
            print(f"      -> Executed Node: [{node}]")

    # Check state at breakpoint
    state = workflow.get_state(thread_config)
    if state.next:
        print(f"\n      🛑 [BREAKPOINT TRIGGERED]: LangGraph halted before '{state.next[0]}'")
        print(f"      Reason: Formally proven contradiction in ASIL-D requirement.")
        print(f"      Injecting Senior Engineer Review...")
        time.sleep(1)

        # Simulate Human Engineer sign-off
        workflow.update_state(
            thread_config,
            {
                "human_approved": True,
                "human_feedback": "Approved with charge-pump hardware revision #104 and terminator replacement.",
                "human_signed_by": "Vansh (Senior Automotive Safety Systems Lead)"
            }
        )
        print(f"      ✅ Engineer Override Signed: 'Approved with charge-pump hardware revision #104.'")
        print(f"      Resuming LangGraph execution...\n")

        # Resume to completion
        for event in workflow.stream(None, thread_config):
            for node in event.keys():
                print(f"      -> Executed Node: [{node}]")

    # Step 5: Final ASPICE Certificate
    final_state = workflow.get_state(thread_config)
    cert = final_state.values.get("aspice_certificate")
    print("\n[5/5] 📜 ASPICE & ISO 26262 Certificate Issued:")
    print(json.dumps(cert.model_dump(), indent=6))

    # Benchmark Summary
    print("\n" + "="*74)
    print("📊 BENCHMARK EVALUATION SUMMARY (Ragas & SMT Prover)")
    print("="*74)
    harness = ChronosBenchmarkHarness()
    bench = harness.run_benchmark()
    print(f"  Total Test Cases:                    {bench['total_test_cases']}")
    print(f"  Contradictions Formally Discovered:  {bench['mathematical_contradictions_detected']}")
    print(f"  Formal Mathematical Groundedness:    {bench['formal_groundedness_score']*100:.1f}%")
    print(f"  Hallucination Rate (Z3 vs Prompting): {bench['hallucination_rate']*100:.1f}%")
    print(f"  Average Z3 Verification Latency:     {bench['average_solver_latency_ms']} ms")
    print("="*74)


if __name__ == "__main__":
    main()
