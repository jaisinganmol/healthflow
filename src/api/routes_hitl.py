from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from src.infrastructure.security.signatures import SignatureService
from src.infrastructure.ehr.factory import get_ehr_client

router = APIRouter(prefix="/api/v1/cases", tags=["Clinician HITL"])

# In-memory registry for pending cases (in production, backed by Postgres checkpointer)
PENDING_CASES: Dict[str, Dict[str, Any]] = {
    "enc-sarah-101": {
        "case_id": "enc-sarah-101",
        "patient_id": "pat-sarah-j",
        "patient_name": "Sarah Johnson",
        "age": 67,
        "procedure": "Total Hip Arthroplasty (CPT 27130)",
        "tier": "TIER_2_REVIEWED",
        "risk_score": 4.5,
        "flags": [
            "FLAG_1_MILD_ANEMIA",
            "FLAG_2_CKD_STAGE_3A",
            "FLAG_3_METFORMIN_PREOP_HOLD",
            "FLAG_4_ASPIRIN_BLEED_RISK",
            "FLAG_5_HIGH_VTE_PROTOCOL"
        ],
        "summary": "Moderate risk: Age 67 with CKD 3a and T2D. Anesthesiologist review required.",
        "status": "PAUSED_AT_CHECKPOINT"
    }
}

# Registered clinician public keys
REGISTERED_CLINICIANS: Dict[str, str] = {}

class ClinicianRegisterKeyRequest(BaseModel):
    clinician_id: str
    public_key_pem: str

class ResumeCaseRequest(BaseModel):
    clinician_id: str
    attestation_decision: str = Field(..., description="APPROVED or REJECTED")
    clinical_notes: str
    signature_base64: str

@router.post("/register-key")
async def register_clinician_key(req: ClinicianRegisterKeyRequest):
    """Registers a clinician's public key for ECDSA signature verification."""
    REGISTERED_CLINICIANS[req.clinician_id] = req.public_key_pem
    return {"status": "REGISTERED", "clinician_id": req.clinician_id}

@router.get("/pending")
async def get_pending_cases():
    """List all cases paused at Tier 2 checkpoints awaiting review."""
    return list(PENDING_CASES.values())

@router.post("/{case_id}/resume")
async def resume_case(case_id: str, request: ResumeCaseRequest):
    """
    Resumes a paused clearance checkpoint.
    Verifies the clinician's ECDSA signature.
    """
    if case_id not in PENDING_CASES:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found or not in pending state")

    public_key = REGISTERED_CLINICIANS.get(request.clinician_id)
    if not public_key:
        raise HTTPException(status_code=400, detail=f"Clinician {request.clinician_id} public key not registered")

    is_valid = SignatureService.verify_attestation(
        public_key_pem=public_key,
        case_id=case_id,
        decision=request.attestation_decision,
        notes=request.clinical_notes,
        signature_b64=request.signature_base64
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cryptographic signature: decision payload has been altered or key mismatch"
        )

    # Commit clearance status back to EHR via FHIR Flag / DocumentReference
    ehr_client = get_ehr_client()
    patient_id = PENDING_CASES[case_id].get("patient_id", "pat-sarah-j")
    clearance_status = "CLEARED" if request.attestation_decision == "APPROVED" else "REJECTED"
    committed = await ehr_client.commit_clearance_status(
        patient_id=patient_id,
        encounter_id=case_id,
        status=clearance_status,
        attestation_signature=request.signature_base64
    )

    # Transition case to resumed/cleared
    PENDING_CASES[case_id]["status"] = clearance_status
    PENDING_CASES[case_id]["attestation_signature"] = request.signature_base64
    PENDING_CASES[case_id]["clearance_committed_to_ehr"] = committed

    return {
        "case_id": case_id,
        "status": PENDING_CASES[case_id]["status"],
        "clearance_committed_to_ehr": committed,
        "clinician_id": request.clinician_id
    }
