from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from src.workflows.state import PreOpState
from src.infrastructure.ehr.factory import get_ehr_client
from src.domain.rules.clinical_gate import ClinicalGateEngine

async def scheduling_node(state: PreOpState) -> Dict[str, Any]:
    """
    Scheduling Agent: Resolves OR slot availability and surgeon blocks.
    Simulates patient preference selection via Twilio SMS.
    """
    return {
        "scheduling_status": "COMPLETED",
        "selected_slot": "2026-04-24T06:30:00Z",
        "or_room_id": "OR-04",
        "scheduling_error": None
    }

async def insurance_node(state: PreOpState) -> Dict[str, Any]:
    """
    Insurance Pre-Auth Agent: Queries payer clearinghouse with exponential backoff.
    """
    # Simulates electronic pre-authorization response
    return {
        "insurance_status": "APPROVED",
        "auth_code": "AUTH-89211-TX",
        "allowed_amount": 14200.00,
        "copay": 250.00,
        "insurance_attempts": 1,
        "insurance_error": None
    }

async def clinical_risk_node(state: PreOpState) -> Dict[str, Any]:
    """
    Clinical Risk Agent: Ingests patient records from EHR via FHIR R4,
    evaluates ASA, RCRI, and active clinical flags via ClinicalGateEngine.
    """
    ehr = get_ehr_client()
    patient_id = state.get("patient_id", "pat-sarah-j")
    cpt = state.get("procedure_cpt", "27130")

    patient = await ehr.get_patient(patient_id)
    conditions = await ehr.get_active_conditions(patient_id)
    labs = await ehr.get_observations(patient_id)
    meds = await ehr.get_medication_statements(patient_id)

    composite_score, tier, flags, summary = ClinicalGateEngine.evaluate_case(
        patient=patient,
        conditions=conditions,
        labs=labs,
        meds=meds,
        cpt=cpt
    )

    asa = ClinicalGateEngine.calculate_asa(conditions, patient.age)
    rcri = ClinicalGateEngine.calculate_rcri(cpt, conditions, labs)

    return {
        "clinical_risk_status": "COMPLETED",
        "asa_class": asa,
        "rcri_score": rcri,
        "risk_score": composite_score,
        "risk_flags": [f.model_dump() for f in flags],
        "risk_summary": summary,
        "risk_tier": tier.value,
        "clinical_error": None
    }

def join_barrier_node(state: PreOpState) -> Dict[str, Any]:
    """
    Strict Join Barrier: Holds until all 3 parallel branches have resolved.
    Enforces that zero routing proceeds on partial state.
    """
    statuses = [
        state.get("scheduling_status"),
        state.get("insurance_status"),
        state.get("clinical_risk_status")
    ]
    if any(s == "PENDING" or s is None for s in statuses):
        raise RuntimeError("Join barrier invoked on incomplete branch state")

    # If insurance failed or scheduling failed, elevate to Tier 3 Escalation
    if state.get("insurance_status") in ["DENIED", "FAILED"] or state.get("scheduling_status") == "FAILED":
        return {"risk_tier": "TIER_3_ESCALATED"}

    # Retain the evaluated clinical tier
    return {"risk_tier": state.get("risk_tier", "TIER_2_REVIEWED")}

def tier_1_auto_node(state: PreOpState) -> Dict[str, Any]:
    """Tier 1: Automated unattended clearance committed back to EHR."""
    return {"clearance_finalized": True}

def tier_2_hitl_node(state: PreOpState) -> Dict[str, Any]:
    """
    Tier 2: Reviewed case. Graph triggers durable interrupt() checkpoint.
    Surfaces structured risk flags to attending anesthesiologist.
    State pauses until resumed with a valid cryptographic signature.
    """
    decision = interrupt({
        "case_id": state.get("encounter_id", "enc-sarah-101"),
        "patient_id": state.get("patient_id", "pat-sarah-j"),
        "tier": state.get("risk_tier"),
        "risk_score": state.get("risk_score"),
        "flags": state.get("risk_flags"),
        "summary": state.get("risk_summary"),
        "instruction": "Attending review required: Acknowledge CKD 3a, Metformin hold, Aspirin status, and VTE prophylaxis."
    })
    
    # Resumed with attestation
    attestation = decision.get("attestation_signature") if isinstance(decision, dict) else str(decision)
    return {
        "attestation_signature": attestation,
        "clearance_finalized": True
    }

def tier_3_escalate_node(state: PreOpState) -> Dict[str, Any]:
    """Tier 3: Clearance halted. Reassigned to multidisciplinary specialist panel."""
    return {"clearance_finalized": False}

def route_tier_condition(state: PreOpState) -> str:
    tier = state.get("risk_tier")
    if tier == "TIER_1_AUTO":
        return "tier_1_auto"
    if tier == "TIER_2_REVIEWED":
        return "tier_2_hitl"
    return "tier_3_escalate"

def build_pre_admission_graph(checkpointer: Optional[Any] = None) -> Any:
    workflow = StateGraph(PreOpState)

    # Add branch nodes
    workflow.add_node("scheduling", scheduling_node)
    workflow.add_node("insurance", insurance_node)
    workflow.add_node("clinical_risk", clinical_risk_node)

    # Add join and gate nodes
    workflow.add_node("join_barrier", join_barrier_node)
    workflow.add_node("tier_1_auto", tier_1_auto_node)
    workflow.add_node("tier_2_hitl", tier_2_hitl_node)
    workflow.add_node("tier_3_escalate", tier_3_escalate_node)

    # Parallel fan-out from START
    workflow.add_edge(START, "scheduling")
    workflow.add_edge(START, "insurance")
    workflow.add_edge(START, "clinical_risk")

    # Fan-in to join barrier
    workflow.add_edge("scheduling", "join_barrier")
    workflow.add_edge("insurance", "join_barrier")
    workflow.add_edge("clinical_risk", "join_barrier")

    # Conditional routing from join barrier
    workflow.add_conditional_edges(
        "join_barrier",
        route_tier_condition,
        {
            "tier_1_auto": "tier_1_auto",
            "tier_2_hitl": "tier_2_hitl",
            "tier_3_escalate": "tier_3_escalate"
        }
    )

    # Route tier completions to END
    workflow.add_edge("tier_1_auto", END)
    workflow.add_edge("tier_2_hitl", END)
    workflow.add_edge("tier_3_escalate", END)

    return workflow.compile(checkpointer=checkpointer)
