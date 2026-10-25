from typing import TypedDict, List, Optional, Literal, Dict, Any

class PreOpState(TypedDict, total=False):
    # Context
    patient_id: str
    encounter_id: str
    procedure_cpt: str
    surgeon_id: str

    # Branch 1: Scheduling
    scheduling_status: Literal["PENDING", "COMPLETED", "FAILED"]
    selected_slot: Optional[str]
    or_room_id: Optional[str]
    scheduling_error: Optional[str]

    # Branch 2: Insurance Pre-Authorization
    insurance_status: Literal["PENDING", "APPROVED", "DENIED", "FAILED"]
    auth_code: Optional[str]
    allowed_amount: Optional[float]
    copay: Optional[float]
    insurance_attempts: int
    insurance_error: Optional[str]

    # Branch 3: Clinical Risk Evaluation
    clinical_risk_status: Literal["PENDING", "COMPLETED", "FAILED"]
    asa_class: Optional[int]
    rcri_score: Optional[int]
    risk_score: Optional[float]
    risk_flags: List[Dict[str, str]]
    risk_summary: Optional[str]
    clinical_error: Optional[str]

    # Gate Decision & Resume State
    risk_tier: Optional[Literal["TIER_1_AUTO", "TIER_2_REVIEWED", "TIER_3_ESCALATED"]]
    attestation_signature: Optional[str]
    clearance_finalized: bool

class PostOpState(TypedDict, total=False):
    patient_id: str
    encounter_id: str
    pod_day: int
    cpt_code: str

    # Discharge Planning
    discharge_cleared: bool
    discharge_summary: Optional[str]
    stability_vitals_passed: bool

    # Follow-Up Symptom Triage
    patient_sms_response: Optional[str]
    parsed_symptoms: Optional[Dict[str, Any]]
    triage_risk_level: Optional[Literal["LOW_RISK", "MODERATE_RISK", "HIGH_RISK"]]
    nurse_escalation_required: bool
    triage_notes: Optional[str]

    # Billing & Coding Audit
    billed_cpt_codes: List[str]
    billed_icd10_codes: List[str]
    discrepancies: List[Dict[str, Any]]
    clean_claim: bool
    allowable_reimbursement: float
