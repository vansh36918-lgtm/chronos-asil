"""
State definitions for Chronos-ASIL LangGraph Workflow.
"""

from typing import List, Optional, Dict, Any, TypedDict
from src.core.models import (
    RequirementItem,
    Z3VerificationResult,
    CANFrameTelemetry,
    OscilloscopeVerdict,
    FaultDiagnosis,
    ASPICECertificate
)


class ChronosAgentState(TypedDict):
    # Ingestion & Specification
    raw_spec_text: str
    requirements: List[RequirementItem]

    # Multimodal Perception & Hardware Telemetry
    can_telemetry_frames: List[CANFrameTelemetry]
    waveform_verdict: Optional[OscilloscopeVerdict]
    waveform_image_path: Optional[str]

    # Formal Verification (Microsoft Z3)
    z3_proof_results: List[Z3VerificationResult]
    has_safety_contradiction: bool

    # Chaos Injection
    fuzzing_events: List[Dict[str, Any]]

    # Human-in-the-Loop (HITL) Controls
    hitl_interrupt_triggered: bool
    human_approved: bool
    human_feedback: Optional[str]
    human_signed_by: Optional[str]

    # Final Diagnosis & Certification
    fault_diagnosis: Optional[FaultDiagnosis]
    aspice_certificate: Optional[ASPICECertificate]
    audit_trail: List[str]
