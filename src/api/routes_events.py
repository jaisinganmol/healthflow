from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from src.workflows.pre_admission import build_pre_admission_graph
from src.workflows.post_discharge import build_post_discharge_graph
from src.infrastructure.persistence.audit_logger import AuditLogger
from langgraph.checkpoint.memory import MemorySaver

router = APIRouter(prefix="/api/v1/events", tags=["EHR Events"])

# Shared memory checkpointer for local execution
SHARED_CHECKPOINTER = MemorySaver()
PREOP_GRAPH = build_pre_admission_graph(checkpointer=SHARED_CHECKPOINTER)
POSTOP_GRAPH = build_post_discharge_graph()
AUDIT_LOGGER = AuditLogger()

class AdmissionEventRequest(BaseModel):
    patient_id: str
    encounter_id: str
    procedure_cpt: str = Field(default="27130", description="CPT procedure code")
    surgeon_id: str = Field(default="dr-ortho-001")

class DischargeEventRequest(BaseModel):
    patient_id: str
    encounter_id: str
    cpt_code: str = Field(default="27130")
    pod_day: int = Field(default=1)
    patient_sms_response: Optional[str] = Field(default="5, no, no, no, no")

@router.post("/admission")
async def handle_admission_event(event: AdmissionEventRequest):
    """
    Ingests an admission surgical order from the EHR.
    Fans out parallel clearance branches: Scheduling, Insurance, and Clinical Risk.
    """
    AUDIT_LOGGER.log_event(
        audit_id=f"aud-admit-{event.encounter_id}",
        actor_id="EHR_TRIGGER",
        patient_id=event.patient_id,
        encounter_id=event.encounter_id,
        action_type="ADMISSION_EVENT_INGESTED",
        resource_accessed=f"Encounter/{event.encounter_id}",
        payload=event.model_dump(),
        clinical_justification="Initiating automated pre-admission clearance pipeline."
    )

    config = {"configurable": {"thread_id": event.encounter_id}}
    initial_input = {
        "patient_id": event.patient_id,
        "encounter_id": event.encounter_id,
        "procedure_cpt": event.procedure_cpt,
        "surgeon_id": event.surgeon_id
    }

    # Execute graph until completion or interrupt checkpoint
    await PREOP_GRAPH.ainvoke(initial_input, config=config)
    state = await PREOP_GRAPH.aget_state(config)

    tier = state.values.get("risk_tier")
    is_cleared = state.values.get("clearance_finalized", False)

    return {
        "encounter_id": event.encounter_id,
        "status": "PAUSED_AT_CHECKPOINT" if tier == "TIER_2_REVIEWED" and not is_cleared else "CLEARED",
        "risk_tier": tier,
        "risk_score": state.values.get("risk_score"),
        "scheduling_status": state.values.get("scheduling_status"),
        "insurance_status": state.values.get("insurance_status"),
        "clinical_risk_status": state.values.get("clinical_risk_status"),
        "flags": state.values.get("risk_flags", []),
        "summary": state.values.get("risk_summary")
    }

@router.post("/discharge")
async def handle_discharge_event(event: DischargeEventRequest):
    """
    Ingests post-discharge check-in event.
    Runs concurrent discharge planning, symptom triage, and billing discrepancy audit.
    """
    AUDIT_LOGGER.log_event(
        audit_id=f"aud-dc-{event.encounter_id}-pod{event.pod_day}",
        actor_id="POST_OP_SCHEDULER",
        patient_id=event.patient_id,
        encounter_id=event.encounter_id,
        action_type="POST_OP_TRIAGE_RUN",
        resource_accessed=f"Encounter/{event.encounter_id}",
        payload=event.model_dump(),
        clinical_justification="Automated post-op day triage check-in and coding discrepancy audit."
    )

    initial_input = {
        "patient_id": event.patient_id,
        "encounter_id": event.encounter_id,
        "cpt_code": event.cpt_code,
        "pod_day": event.pod_day,
        "patient_sms_response": event.patient_sms_response
    }

    result = await POSTOP_GRAPH.ainvoke(initial_input)

    return {
        "encounter_id": event.encounter_id,
        "pod_day": event.pod_day,
        "discharge_cleared": result.get("discharge_cleared"),
        "triage_risk_level": result.get("triage_risk_level"),
        "nurse_escalation_required": result.get("nurse_escalation_required"),
        "triage_notes": result.get("triage_notes"),
        "clean_claim": result.get("clean_claim"),
        "discrepancies": result.get("discrepancies", []),
        "allowable_reimbursement": result.get("allowable_reimbursement")
    }

@router.get("/patients/search")
async def search_ehr_patients(
    family: Optional[str] = None,
    given: Optional[str] = None,
    limit: int = 10
):
    """
    Dynamically search patients from Epic on FHIR (or configured EHR).
    """
    from src.infrastructure.ehr.factory import get_ehr_client
    ehr = get_ehr_client()
    try:
        patients = await ehr.search_patients(family=family, given=given, limit=limit)
        return {
            "count": len(patients),
            "patients": [p.model_dump() for p in patients]
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"EHR search failed: {str(e)}")
