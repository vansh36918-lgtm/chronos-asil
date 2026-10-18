"""
Streamlit Web Dashboard for Chronos-ASIL.
Visualizes real-time CAN bus telemetry, Z3 formal proofs,
multimodal oscilloscope waveforms, and the LangGraph Human-in-the-Loop (HITL) review gate.
"""

import os
import streamlit as st
import pandas as pd
from src.core.models import RequirementItem, ASILRating
from src.formal.z3_verifier import Z3SafetyVerifier
from src.telemetry.can_bus import AutomotiveCANInterface
from src.telemetry.fuzzer import CANChaosFuzzer
from src.vision.waveform_analyzer import OscilloscopeWaveformAnalyzer
from src.agent.graph import create_chronos_workflow

st.set_page_config(page_title="Chronos-ASIL | FORVIA HELLA", page_icon="⚡", layout="wide")

st.markdown("""
# ⚡ Chronos-ASIL: Autonomous ECU Triage & Formal Verification
### **FORVIA HELLA Advanced Safety & Lighting Systems Lab (ISO 26262 ASIL-D / ASPICE)**
---
""")

# Sidebar Controls
st.sidebar.header("🔧 Configuration & Controls")
subsystem_choice = st.sidebar.selectbox(
    "Automotive Subsystem",
    ["Matrix LED Headlamp Controller", "77 GHz Forward Radar ECU", "Smart Battery Gateway"]
)

cold_crank_voltage = st.sidebar.slider("Cold-Crank Voltage (V)", 5.0, 9.0, 6.2, 0.1)
demanded_latency_ms = st.sidebar.slider("Required Response Time (ms)", 20.0, 250.0, 60.0, 10.0)

# Generate sample waveform if needed
os.makedirs("data/waveforms", exist_ok=True)
nominal_img = "data/waveforms/nominal_can.png"
fault_img = "data/waveforms/ringing_termination_fault.png"
analyzer = OscilloscopeWaveformAnalyzer()
if not os.path.exists(nominal_img):
    analyzer.generate_synthetic_waveform(nominal_img, fault_type=None)
if not os.path.exists(fault_img):
    analyzer.generate_synthetic_waveform(fault_img, fault_type="RINGING_MISSING_TERMINATION")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📐 Formal Verification (Z3)",
    "📡 Real-Time CAN Bus",
    "👁️ Multimodal Waveforms",
    "🛑 LangGraph Human-in-the-Loop"
])

with tab1:
    st.subheader("1. Microsoft Z3 SMT Theorem Prover (Zero Hallucination)")
    st.markdown("""
    Evaluates whether the specification's cold-crank operating parameters mathematically violate
    underlying semiconductor gate-driver physics (ISO 26262 ASIL-D).
    """)

    sample_req = RequirementItem(
        req_id="REQ-HL-ASIL-D-01",
        subsystem=subsystem_choice.replace(" ", "_"),
        description=f"System must complete emergency high-beam trigger within {demanded_latency_ms}ms during cold crank down to {cold_crank_voltage}V.",
        asil_level=ASILRating.ASIL_D,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=cold_crank_voltage,
        t_response_max_ms=demanded_latency_ms,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )

    verifier = Z3SafetyVerifier()
    proof = verifier.verify_requirement_consistency(sample_req)

    if proof.status.value == "PROVEN_CONTRADICTION":
        st.error(f"🔴 **MATHEMATICALLY PROVEN CONTRADICTION (UNSAT)**")
        st.write(proof.proof_explanation)
        st.json(proof.counterexample)
    else:
        st.success(f"🟢 **FORMALLY VERIFIED (SAT)**: All timing and voltage invariants hold.")
        st.json(proof.counterexample)

with tab2:
    st.subheader("2. Automotive CAN Bus Telemetry & Chaos Fuzzing")
    col1, col2 = st.columns([2, 1])

    with col1:
        can_bus = AutomotiveCANInterface(interface="virtual")
        # Send a sample batch
        can_bus.send_frame(can_bus.pack_headlamp_frame(current_ma=4350, duty_cycle_pct=85.0, temp_c=88))
        can_bus.send_frame(can_bus.pack_power_frame(voltage_v=cold_crank_voltage, impedance_ohm=118.5))
        frames = can_bus.read_telemetry_stream(max_frames=4, timeout=0.1)
        can_bus.shutdown()

        records = []
        for f in frames:
            records.append({
                "Timestamp": f"{f.timestamp:.3f}",
                "Arb ID": hex(f.arbitration_id),
                "Payload Hex": f.payload_hex,
                "Signals": str(f.decoded_signals),
                "Anomaly": f.anomaly_detected or "Nominal"
            })
        st.dataframe(pd.DataFrame(records), use_container_width=True)

    with col2:
        st.markdown("#### Chaos Injection Tool")
        if st.button("💥 Inject Acute Cold Crank Voltage Drop (6.2V)"):
            fuzzer = CANChaosFuzzer(AutomotiveCANInterface(interface="virtual"))
            res = fuzzer.inject_undervoltage_cold_crank(target_voltage=6.2)
            st.warning(f"Injected fault: {res['fault_type']} ({res['voltage_injected_v']}V)")

with tab3:
    st.subheader("3. Multimodal Oscilloscope Waveform Inspection")
    wcol1, wcol2 = st.columns(2)

    with wcol1:
        st.markdown("**Nominal CAN Waveform (Differential Vdiff = 2.0V)**")
        st.image(nominal_img)
        v_nom = analyzer.analyze_waveform(nominal_img)
        st.success(v_nom.diagnosis)

    with wcol2:
        st.markdown("**Damaged 120Ω Terminator (Signal Reflections & Ringing)**")
        st.image(fault_img)
        v_fault = analyzer.analyze_waveform(fault_img)
        st.error(v_fault.diagnosis)

with tab4:
    st.subheader("4. LangGraph Stateful Agent with Human-in-the-Loop Breakpoint")
    st.markdown("""
    The agent pauses execution at the `interrupt_before` checkpoint if a formal contradiction is proven.
    A Senior Safety Engineer must review and provide sign-off to proceed to ASPICE certification.
    """)

    if st.button("🚀 Run Full LangGraph Diagnostic Workflow"):
        workflow = create_chronos_workflow()
        thread_config = {"configurable": {"thread_id": "session-hella-001"}}

        initial_state = {
            "raw_spec_text": "Sample Automotive Spec",
            "requirements": [sample_req],
            "waveform_image_path": fault_img,
            "audit_trail": [],
            "human_approved": False,
            "human_feedback": None,
            "human_signed_by": None
        }

        # Run until breakpoint or completion
        events = list(workflow.stream(initial_state, thread_config))
        st.write("#### Execution Audit Trail:")
        for event in events:
            for node, output in event.items():
                st.info(f"**Step [{node}] executed.**")
                if "audit_trail" in output:
                    for line in output["audit_trail"]:
                        st.text(line)

        # Check state after interrupt
        current_state = workflow.get_state(thread_config)
        if current_state.next:
            st.warning(f"⏸️ **LANGGRAPH EXECUTION PAUSED**: Awaiting human sign-off before node: `{current_state.next}`")
            approver_name = st.text_input("Engineer Name:", value="Vansh (Senior Safety Engineer)")
            feedback = st.text_area("Engineering Justification / Hardware Override:", "Approved with charge-pump hardware revision.")

            if st.button("✅ Approve & Resume Execution"):
                # Update state and resume
                workflow.update_state(
                    thread_config,
                    {"human_approved": True, "human_feedback": feedback, "human_signed_by": approver_name}
                )
                resume_events = list(workflow.stream(None, thread_config))
                st.success("🎉 **Workflow Resumed to Completion! ASPICE Certificate Issued.**")
                final_state = workflow.get_state(thread_config)
                st.json(final_state.values.get("aspice_certificate").model_dump())
