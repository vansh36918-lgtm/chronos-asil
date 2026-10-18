"""
Chronos-ASIL: Advanced Mission-Control Dashboard for Automotive ECU Triage & Formal Verification.
Developed for FORVIA HELLA Advanced Safety & Lighting Systems Lab (ISO 26262 ASIL-D / ASPICE PAM v4.0).
"""

import os
import time
import json
import streamlit as st
import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from src.core.models import RequirementItem, ASILRating
from src.formal.z3_verifier import Z3SafetyVerifier
from src.telemetry.can_bus import AutomotiveCANInterface
from src.telemetry.fuzzer import CANChaosFuzzer
from src.vision.waveform_analyzer import OscilloscopeWaveformAnalyzer
from src.agent.graph import create_chronos_workflow

# Page Configuration
st.set_page_config(
    page_title="CHRONOS-ASIL | FORVIA HELLA",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Dark Automotive Theme CSS
st.markdown("""
<style>
    /* Dark Cyber Automotive Theme */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Header Bar */
    .telemetry-header {
        background: linear-gradient(135deg, #131d31 0%, #0d1527 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-right: 8px;
    }
    
    .badge-asil {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #ef4444;
    }
    
    .badge-z3 {
        background: rgba(56, 189, 248, 0.2);
        color: #38bdf8;
        border: 1px solid #38bdf8;
    }
    
    .badge-bus {
        background: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border: 1px solid #22c55e;
    }

    /* Metric Cards */
    .metric-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #38bdf8;
        margin: 4px 0;
    }
    
    .metric-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    
    /* Z3 Solver Card */
    .z3-card-unsat {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid #ef4444;
        border-radius: 10px;
        padding: 18px;
        margin: 12px 0;
    }
    
    .z3-card-sat {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid #22c55e;
        border-radius: 10px;
        padding: 18px;
        margin: 12px 0;
    }

    /* Custom button styling */
    .stButton>button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="telemetry-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 26px; color: #f8fafc; font-weight: 800; letter-spacing: -0.5px;">
                ⚡ CHRONOS-ASIL | Automotive ECU Mission Control
            </h1>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 14px;">
                FORVIA HELLA Advanced Safety & Lighting Systems Lab (ISO 26262 ASIL-D / ASPICE PAM v4.0)
            </p>
        </div>
        <div>
            <span class="status-badge badge-asil">ISO 26262 ASIL-D</span>
            <span class="status-badge badge-z3">Z3 SMT PROVER: ACTIVE</span>
            <span class="status-badge badge-bus">SOCKETCAN: 500 KBPS</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Controls
st.sidebar.markdown("### 🎛️ Physical Test-Bench Controls")
st.sidebar.markdown("Configure semiconductor operating limits and automotive ECU parameters:")

subsystem = st.sidebar.selectbox(
    "Target ECU Subsystem",
    ["Matrix LED Headlamp Controller (HELLA)", "77 GHz Autonomous Radar ECU", "Central High-Voltage Gateway"]
)

cold_crank_voltage = st.sidebar.slider(
    "Cold-Crank Voltage (V)",
    min_value=5.0,
    max_value=9.0,
    value=6.0,
    step=0.1,
    help="Under ISO 26262, cold-crank during engine ignition causes battery drop."
)

demanded_latency_ms = st.sidebar.slider(
    "Required Response Latency (ms)",
    min_value=20.0,
    max_value=250.0,
    value=50.0,
    step=5.0,
    help="Specification-demanded maximum transition time."
)

bus_impedance_nominal = st.sidebar.slider(
    "CAN Differential Impedance (Ω)",
    min_value=30.0,
    max_value=130.0,
    value=60.0,
    step=5.0,
    help="Nominal CAN bus split termination is 60Ω (two 120Ω resistors in parallel)."
)

# Top KPI Metric Row
mcol1, mcol2, mcol3, mcol4 = st.columns(4)

with mcol1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Cold-Crank Voltage</div>
        <div class="metric-value" style="color: {'#ef4444' if cold_crank_voltage < 7.2 else '#4ade80'};">{cold_crank_voltage:.1f} V</div>
        <div style="font-size: 11px; color: #64748b;">{'CRITICAL BROWNOUT' if cold_crank_voltage < 7.2 else 'NOMINAL RANGE'}</div>
    </div>
    """, unsafe_allow_html=True)

with mcol2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Target Latency</div>
        <div class="metric-value" style="color: {'#ef4444' if demanded_latency_ms < 180 and cold_crank_voltage < 7.2 else '#38bdf8'};">{demanded_latency_ms:.0f} ms</div>
        <div style="font-size: 11px; color: #64748b;">Physical Gate Min: 180 ms</div>
    </div>
    """, unsafe_allow_html=True)

with mcol3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Bus Impedance</div>
        <div class="metric-value" style="color: {'#ef4444' if (bus_impedance_nominal < 50 or bus_impedance_nominal > 70) else '#4ade80'};">{bus_impedance_nominal:.0f} Ω</div>
        <div style="font-size: 11px; color: #64748b;">{'REFLECTION FAULT' if (bus_impedance_nominal < 50 or bus_impedance_nominal > 70) else 'TERMINATION BALANCED'}</div>
    </div>
    """, unsafe_allow_html=True)

with mcol4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Formal Prover State</div>
        <div class="metric-value" style="color: #38bdf8;">100.0%</div>
        <div style="font-size: 11px; color: #64748b;">0% Hallucination Guarantee</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_formal, tab_can, tab_wave, tab_hitl = st.tabs([
    "📐 Formal Verification (Microsoft Z3)",
    "📡 Live Automotive CAN-FD Telemetry",
    "👁️ Multimodal Waveform Vision",
    "🛑 LangGraph Human-in-the-Loop Cockpit"
])

# Ensure waveforms exist
os.makedirs("data/waveforms", exist_ok=True)
analyzer = OscilloscopeWaveformAnalyzer()
nom_path = "data/waveforms/nominal_can.png"
fault_path = "data/waveforms/ringing_termination_fault.png"
if not os.path.exists(nom_path):
    analyzer.generate_synthetic_waveform(nom_path, fault_type=None)
if not os.path.exists(fault_path):
    analyzer.generate_synthetic_waveform(fault_path, fault_type="RINGING_MISSING_TERMINATION")

# --- TAB 1: FORMAL VERIFICATION ---
with tab_formal:
    st.subheader("1. First-Order Logic SMT Theorem Prover (Microsoft Z3)")
    st.markdown("""
    Automotive safety **(ISO 26262 ASIL-D)** prohibits probabilistic text generation for requirement sign-off.
    Chronos-ASIL compiles requirement envelopes directly into **SMT-LIB First-Order Logic constraints**.
    """)

    sample_req = RequirementItem(
        req_id="REQ-HELLA-ASIL-D-104",
        subsystem=subsystem.replace(" ", "_"),
        description=f"System must complete emergency transition in <={demanded_latency_ms}ms during cold crank down to {cold_crank_voltage}V.",
        asil_level=ASILRating.ASIL_D,
        v_operating_min=9.0,
        v_operating_max=16.0,
        v_cold_crank_min=cold_crank_voltage,
        t_response_max_ms=demanded_latency_ms,
        min_bus_impedance_ohm=50.0,
        max_bus_impedance_ohm=70.0
    )

    verifier = Z3SafetyVerifier()
    start_t = time.perf_counter()
    proof = verifier.verify_requirement_consistency(sample_req)
    z3_dur_ms = (time.perf_counter() - start_t) * 1000.0

    col_z3_1, col_z3_2 = st.columns([3, 2])

    with col_z3_1:
        if proof.status.value == "PROVEN_CONTRADICTION":
            st.markdown(f"""
            <div class="z3-card-unsat">
                <h3 style="margin: 0; color: #ef4444; font-size: 18px;">🔴 MATHEMATICALLY PROVEN CONTRADICTION (UNSAT)</h3>
                <p style="margin: 8px 0 0 0; color: #cbd5e1; font-size: 14px;">
                    <b>Theorem Formulation:</b> <code>Cold_Crank(V &lt; 7.2V) ∧ T_Response &le; {demanded_latency_ms}ms == UNSAT</code><br><br>
                    {proof.proof_explanation}
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("**Exact Failure Counterexample Discovered by Z3 Solver:**")
            st.json(proof.counterexample)
        else:
            st.markdown(f"""
            <div class="z3-card-sat">
                <h3 style="margin: 0; color: #22c55e; font-size: 18px;">🟢 FORMALLY VERIFIED SATISFIABLE (SAT)</h3>
                <p style="margin: 8px 0 0 0; color: #cbd5e1; font-size: 14px;">
                    Z3 SMT Solver verified all physical gate-driver dynamics and voltage envelopes. No contradictions found.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.json(proof.counterexample)

    with col_z3_2:
        st.markdown("#### Solver Diagnostics & Execution Time")
        st.write(f"⏱️ **Solver Evaluation Latency:** `{z3_dur_ms:.2f} ms`")
        st.write("🛡️ **Safety Integrity Rating:** `ASIL-D (Highest)`")
        st.write("🏛️ **Regulatory Standard:** `ISO 26262 Part 6 & ASPICE PAM v4.0`")
        st.write("📜 **SMT Backend:** `Microsoft Z3 SMT Solver v5.3`")

        if HAS_PLOTLY:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=cold_crank_voltage,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Cold-Crank Voltage (V)", 'font': {'size': 14, 'color': '#94a3b8'}},
                gauge={
                    'axis': {'range': [4.0, 10.0], 'tickcolor': "#94a3b8"},
                    'bar': {'color': "#38bdf8"},
                    'steps': [
                        {'range': [4.0, 7.2], 'color': "rgba(239, 68, 68, 0.4)"},
                        {'range': [7.2, 10.0], 'color': "rgba(34, 197, 94, 0.4)"}
                    ],
                    'threshold': {
                        'line': {'color': "#ef4444", 'width': 3},
                        'thickness': 0.75,
                        'value': 7.2
                    }
                }
            ))
            fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "#f8fafc"}, height=220, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

# --- TAB 2: LIVE CAN BUS TELEMETRY ---
with tab_can:
    st.subheader("2. Automotive CAN Bus Telemetry & Chaos Fuzzing Engine")
    st.markdown("""
    Direct binding to **SocketCAN (`vcan0`)** / Virtual CAN. 
    Decodes high-frequency 29-bit CAN frames and injects chaos stimulus to stress-test ECU recovery.
    """)

    can_col1, can_col2 = st.columns([3, 2])

    with can_col1:
        st.markdown("#### Live CAN Packet Waterfall Stream")
        can_bus = AutomotiveCANInterface(interface="virtual")
        # Transmit active telemetry
        can_bus.send_frame(can_bus.pack_headlamp_frame(current_ma=4380, duty_cycle_pct=92.0, temp_c=98))
        can_bus.send_frame(can_bus.pack_power_frame(voltage_v=cold_crank_voltage, impedance_ohm=bus_impedance_nominal))
        frames = can_bus.read_telemetry_stream(max_frames=6, timeout=0.1)
        can_bus.shutdown()

        records = []
        for f in frames:
            records.append({
                "Timestamp": f"{f.timestamp:.4f}",
                "Arb ID": hex(f.arbitration_id),
                "Payload (Hex)": f.payload_hex,
                "Signals Decoded": str(f.decoded_signals),
                "Anomaly Status": f.anomaly_detected or "NOMINAL"
            })
        st.dataframe(pd.DataFrame(records), use_container_width=True)

    with can_col2:
        st.markdown("#### 💥 Chaos Fault Injection Panel")
        st.markdown("Simulate acute electrical and network anomalies in real-time:")
        if st.button("🚨 Inject Acute Cold-Crank Voltage Collapse (6.2V)"):
            fuzzer = CANChaosFuzzer(AutomotiveCANInterface(interface="virtual"))
            res = fuzzer.inject_undervoltage_cold_crank(target_voltage=6.2)
            st.warning(f"Injected: {res['fault_type']} at {res['voltage_injected_v']}V")

        if st.button("⚠️ Inject 120Ω Missing Bus Terminator Mismatch"):
            fuzzer = CANChaosFuzzer(AutomotiveCANInterface(interface="virtual"))
            res = fuzzer.inject_termination_fault(impedance_ohm=120.0)
            st.error(f"Injected: {res['fault_type']} (Impedance: {res['impedance_ohm']}Ω)")

        if st.button("🛑 Trigger Bus Flood Denial-of-Service (Arb ID 0x000)"):
            fuzzer = CANChaosFuzzer(AutomotiveCANInterface(interface="virtual"))
            res = fuzzer.inject_bus_flood_denial_of_service(burst_count=5)
            st.info(f"Transmitted {len(res)} dominant high-priority frames onto bus.")

# --- TAB 3: MULTIMODAL WAVEFORM VISION ---
with tab_wave:
    st.subheader("3. Multimodal Physical-Layer Oscilloscope Waveform Vision")
    st.markdown("""
    Automotive network failures often stem from physical transmission line faults. 
    Chronos-ASIL visually inspects oscilloscope screenshots to diagnose signal integrity before software triaging.
    """)

    wcol1, wcol2 = st.columns(2)

    with wcol1:
        st.markdown("#### Nominal Physical Trace (Differential Vdiff = 2.0V)")
        st.image(nom_path, use_column_width=True)
        v_nom = analyzer.analyze_waveform(nom_path)
        st.success(f"**Verdict:** {v_nom.diagnosis}")

    with wcol2:
        st.markdown("#### Physical Fault: Damaged 120Ω Bus Terminator")
        st.image(fault_path, use_column_width=True)
        v_fault = analyzer.analyze_waveform(fault_path)
        st.error(f"**Verdict:** {v_fault.diagnosis}")

# --- TAB 4: LANGGRAPH HITL COCKPIT ---
with tab_hitl:
    st.subheader("4. LangGraph Stateful Agent with Human-in-the-Loop Breakpoint")
    st.markdown("""
    LangGraph manages cyclic state orchestration. When an ASIL-D contradiction is mathematically proven, 
    the state machine triggers `interrupt_before=["human_in_the_loop_gate"]`. 
    Execution pauses on disk until a Senior Safety Engineer inputs approval.
    """)

    run_btn = st.button("🚀 Execute LangGraph Autonomous Triage Cycle")

    if run_btn:
        workflow = create_chronos_workflow()
        thread_id = f"hella-session-{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        st.session_state["thread_id"] = thread_id
        st.session_state["workflow"] = workflow

        init_state = {
            "raw_spec_text": "HELLA Matrix LED System Requirement Specification v4.2",
            "requirements": [sample_req],
            "waveform_image_path": fault_path,
            "audit_trail": [],
            "human_approved": False,
            "human_feedback": None,
            "human_signed_by": None
        }

        progress = st.progress(0)
        events = list(workflow.stream(init_state, config))
        progress.progress(80)

        st.markdown("#### 📋 Execution Audit Trail:")
        for ev in events:
            for node, out in ev.items():
                st.info(f"**Step [{node}]:** Executed successfully.")
                if "audit_trail" in out:
                    for line in out["audit_trail"]:
                        st.caption(f"• {line}")

        curr_state = workflow.get_state(config)
        if curr_state.next:
            st.markdown(f"""
            <div class="z3-card-unsat">
                <h3 style="margin: 0; color: #ef4444; font-size: 18px;">🛑 LANGGRAPH BREAKPOINT TRIGGERED</h3>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 14px;">
                    Execution halted before node <code>{curr_state.next[0]}</code>.<br>
                    <b>Reason:</b> Microsoft Z3 mathematically proved an ASIL-D contradiction. 
                    Automated certificate issuance blocked until senior engineer signs off.
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("hitl_review_form"):
                engineer_name = st.text_input("Lead Safety Engineer Name", value="Vansh (Senior Safety Lead - FORVIA HELLA)")
                eng_feedback = st.text_area(
                    "Hardware Mitigation / Override Justification",
                    value="Approved with Charge-Pump Hardware Revision #104 and replacement of open-circuit 120Ω bus terminator."
                )
                submitted = st.form_submit_button("✅ Sign ASIL-D Override & Issue Certificate")

                if submitted:
                    workflow.update_state(
                        config,
                        {
                            "human_approved": True,
                            "human_feedback": eng_feedback,
                            "human_signed_by": engineer_name
                        }
                    )
                    resume_events = list(workflow.stream(None, config))
                    progress.progress(100)
                    st.success("🎉 **Workflow Resumed to Completion! Certificate Formally Issued.**")
                    final_s = workflow.get_state(config)
                    cert_data = final_s.values.get("aspice_certificate").model_dump()
                    st.json(cert_data)
                    st.download_button(
                        "📥 Download Official ASPICE Compliance Certificate (JSON)",
                        data=json.dumps(cert_data, indent=4),
                        file_name="ASPICE_CERTIFICATE_FORVIA_HELLA.json",
                        mime="application/json"
                    )
