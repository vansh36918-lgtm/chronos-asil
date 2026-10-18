"""
Core Pydantic data models for Chronos-ASIL.
Defines schemas for automotive requirements, CAN telemetry, formal Z3 proofs,
multimodal waveform results, and ASPICE certification.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ASILRating(str, Enum):
    QM = "QM"          # Quality Management (Non-safety critical)
    ASIL_A = "ASIL-A"  # Lowest automotive safety integrity level
    ASIL_B = "ASIL-B"  # Moderate safety integrity
    ASIL_C = "ASIL-C"  # High safety integrity
    ASIL_D = "ASIL-D"  # Highest automotive safety integrity (Steering, Braking, Matrix Beams)


class Z3ProofStatus(str, Enum):
    SATISFIABLE = "SATISFIABLE"
    PROVEN_CONTRADICTION = "PROVEN_CONTRADICTION"
    UNVERIFIED = "UNVERIFIED"


class RequirementItem(BaseModel):
    req_id: str = Field(description="Unique Requirement ID (e.g. REQ-HL-ASIL-D-01)")
    subsystem: str = Field(description="Subsystem name, e.g. Matrix_Headlamp_Driver")
    description: str = Field(description="Natural language requirement statement")
    asil_level: ASILRating = Field(default=ASILRating.ASIL_B)
    v_operating_min: float = Field(default=9.0, description="Minimum operating voltage (V)")
    v_operating_max: float = Field(default=16.0, description="Maximum operating voltage (V)")
    v_cold_crank_min: float = Field(default=6.0, description="Minimum voltage during cold crank (V)")
    t_response_max_ms: float = Field(default=100.0, description="Maximum response time in milliseconds")
    min_bus_impedance_ohm: float = Field(default=50.0, description="Minimum allowable CAN differential impedance")
    max_bus_impedance_ohm: float = Field(default=70.0, description="Maximum allowable CAN differential impedance (Nominal: 60 ohm)")


class Z3VerificationResult(BaseModel):
    status: Z3ProofStatus
    req_id: str
    theorem_statement: str
    proof_explanation: str
    counterexample: Optional[Dict[str, Any]] = None
    violated_invariants: List[str] = Field(default_factory=list)


class CANFrameTelemetry(BaseModel):
    timestamp: float
    arbitration_id: int
    payload_hex: str
    is_error_frame: bool = False
    is_extended: bool = False
    decoded_signals: Dict[str, float] = Field(default_factory=dict)
    anomaly_detected: Optional[str] = None


class OscilloscopeVerdict(BaseModel):
    image_name: str
    ringing_detected: bool
    ground_bounce_detected: bool
    termination_impedance_fault: bool
    differential_voltage_v: float
    diagnosis: str
    confidence: float


class FaultDiagnosis(BaseModel):
    incident_id: str
    root_cause: str
    severity: str
    confidence_score: float
    formally_proven_conflict: bool
    affected_ecu: str
    can_anomaly_observed: Optional[str] = None
    z3_proof_summary: Optional[str] = None
    recommended_mitigation: str


class ASPICECertificate(BaseModel):
    certificate_id: str
    generated_at: str
    project_name: str = "FORVIA HELLA Advanced Lighting & Radar Platform"
    standard: str = "ISO 26262 Part 6 & Automotive SPICE (ASPICE) PAM v4.0"
    total_requirements_analyzed: int
    formally_verified_sat: int
    unresolvable_contradictions: int
    asil_d_compliance_status: str
    human_in_the_loop_approver: Optional[str] = None
    formal_proof_engine: str = "Microsoft Z3 SMT Theorem Prover v5.x"
