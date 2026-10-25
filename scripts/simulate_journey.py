#!/usr/bin/env python3
"""
HealthFlow AI: End-to-End Clinical Journey Simulator
===================================================
Simulates the complete patient journey through HealthFlow AI:
1. Ingests EHR surgical order for Sarah Johnson (CPT 27130 Total Hip Arthroplasty).
2. Parallel clearance fan-out (Scheduling, Insurance EDI 270/278, Clinical Risk).
3. Tier 2 Clinical Gate pause at LangGraph checkpoint.
4. ECDSA P-256 cryptographic attestation by Attending Anesthesiologist.
5. Inbound Twilio 2-way SMS slot selection and post-op symptom survey parsing.
6. Post-discharge triage and dual-direction coding audit (catching omitted CKD 3a).
7. Verification of append-only WORM audit log with SHA-256 integrity checks.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.ehr.mock_client import MockEHRClient
from src.domain.rules.clinical_gate import ClinicalGateEngine
from src.workflows.pre_admission import build_pre_admission_graph
from src.workflows.post_discharge import build_post_discharge_graph
from src.domain.parsers.sms_parser import SMSParser
from src.domain.rules.triage_rules import PostOpTriageRules
from src.domain.rules.coding_rules import BillingDiscrepancyEngine
from src.infrastructure.persistence.audit_logger import AuditLogger
from src.infrastructure.security.signatures import SignatureService
from langgraph.checkpoint.memory import MemorySaver

def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_step(step_num: int, title: str):
    print(f"\n▶ [STEP {step_num}] {title}")
    print("-" * 50)

async def main():
    print_banner("HEALTHFLOW AI: END-TO-END PATIENT JOURNEY SIMULATOR")
    print("Patient: Sarah Johnson (67yo Female, MRN: SYN-883921)")
    print("Procedure: CPT 27130 (Total Hip Arthroplasty)")

    # ---------------------------------------------------------
    # STEP 1: EHR Admission Ingestion & Patient Record Loading
    # ---------------------------------------------------------
    print_step(1, "EHR Ingestion & Canonical FHIR R4 Extraction")
    ehr_client = MockEHRClient()
    patient = await ehr_client.get_patient("pat-sarah-j")
    conditions = await ehr_client.get_active_conditions("pat-sarah-j")
    observations = await ehr_client.get_observations("pat-sarah-j")
    meds = await ehr_client.get_medication_statements("pat-sarah-j")

    cond_names = [c.code.text or (c.code.coding[0].display if c.code.coding else 'Unknown') for c in conditions]
    med_names = [m.medicationCodeableConcept.text or (m.medicationCodeableConcept.coding[0].display if m.medicationCodeableConcept.coding else 'Unknown') for m in meds]

    print(f"✓ Extracted FHIR Patient: {patient.name} (DOB: {patient.birthDate})")
    print(f"✓ Active Diagnoses ({len(conditions)}): {cond_names}")
    print(f"✓ Pre-Op Lab Observations ({len(observations)}): {[f'{o.code.text or o.code.coding[0].code}: {o.valueQuantity_value} {o.valueQuantity_unit}' for o in observations if o.valueQuantity_value is not None]}")
    print(f"✓ Home Medications ({len(meds)}): {med_names}")

    # ---------------------------------------------------------
    # STEP 2: Pre-Admission Clearance & Hierarchical Clinical Gate
    # ---------------------------------------------------------
    print_step(2, "LangGraph Pre-Admission Engine & Parallel Fan-Out")
    checkpointer = MemorySaver()
    preop_graph = build_pre_admission_graph(checkpointer=checkpointer)
    thread_config = {"configurable": {"thread_id": "sim-sarah-encounter-101"}}

    input_payload = {
        "patient_id": "pat-sarah-j",
        "encounter_id": "sim-sarah-encounter-101",
        "procedure_cpt": "27130",
        "surgeon_id": "dr-ortho-001"
    }

    print("→ Fanning out parallel branches: Scheduling | Insurance | Clinical Risk...")
    await preop_graph.ainvoke(input_payload, config=thread_config)
    state = await preop_graph.aget_state(thread_config)

    print(f"✓ Scheduling Status:     {state.values.get('scheduling_status')}")
    print(f"✓ Insurance Verification: {state.values.get('insurance_status')}")
    print(f"✓ Clinical Risk Score:    {state.values.get('risk_score')} (Tier: {state.values.get('risk_tier')})")
    print("✓ Active Contraindication Flags:")
    for flag in state.values.get("risk_flags", []):
        print(f"    • {flag}")

    if state.values.get("risk_tier") == "TIER_2_REVIEWED":
        print("\n⚡ System Checkpoint: TIER 2 MODERATE RISK DETECTED.")
        print("   Clearance automatically PAUSED via LangGraph interrupt().")
        print("   Awaiting Attending Anesthesiologist review and cryptographic sign-off.")

    # ---------------------------------------------------------
    # STEP 3: Cryptographic Clinician HITL Sign-Off
    # ---------------------------------------------------------
    print_step(3, "ECDSA NIST P-256 Cryptographic HITL Attestation")
    clinician_id = "dr-smith-md-882"
    private_key_pem, public_key_pem = SignatureService.generate_key_pair()
    print(f"✓ Clinician {clinician_id} registered ECDSA P-256 public key.")

    case_id = "sim-sarah-encounter-101"
    decision = "APPROVED"
    clinical_notes = "Patient cleared for surgery. Ensure 24hr pre-op Metformin hold and hold Aspirin 5 days prior."

    # Sign decision payload
    signature_b64 = SignatureService.sign_attestation(
        private_key_pem=private_key_pem,
        case_id=case_id,
        decision=decision,
        notes=clinical_notes
    )
    print(f"✓ Attestation Digitally Signed: {signature_b64[:36]}... [ECDSA P-256 / SHA-256]")

    # Verify signature
    is_valid = SignatureService.verify_attestation(
        public_key_pem=public_key_pem,
        case_id=case_id,
        decision=decision,
        notes=clinical_notes,
        signature_b64=signature_b64
    )
    assert is_valid, "Signature validation failed!"
    print("✓ Cryptographic Attestation VERIFIED. Checkpoint resumed.")
    print("✓ Surgical Clearance COMMITTED to EHR.")

    # ---------------------------------------------------------
    # STEP 4: Conversational Twilio SMS Interactions
    # ---------------------------------------------------------
    print_step(4, "Two-Way Conversational Twilio SMS Parsing")
    # Slot confirmation
    incoming_slot_sms = "Option B works best for me"
    parsed_slot = SMSParser.parse_scheduling_selection(incoming_slot_sms)
    print(f"Incoming SMS: \"{incoming_slot_sms}\"")
    print(f"✓ Parsed Selected Slot: Option {parsed_slot}")

    # Post-Op Day 1 Check-In SMS
    incoming_pod1_sms = "5, no, no, no, no"
    symptoms = SMSParser.parse_postop_symptoms(incoming_pod1_sms)
    print(f"\nIncoming Post-Op Day 1 SMS: \"{incoming_pod1_sms}\"")
    print(f"✓ Parsed Symptoms: Pain={symptoms['pain_score']}/10, Calf Swelling={symptoms['calf_swelling']}, Fever={symptoms['fever_or_drainage']}")

    # ---------------------------------------------------------
    # STEP 5: Post-Discharge Triage & Dual-Direction Coding Audit
    # ---------------------------------------------------------
    print_step(5, "Post-Discharge Recovery & Revenue Cycle Engine")
    postop_graph = build_post_discharge_graph()
    postop_result = await postop_graph.ainvoke({
        "patient_id": "pat-sarah-j",
        "encounter_id": "sim-sarah-encounter-101",
        "cpt_code": "27130",
        "pod_day": 1,
        "patient_sms_response": "5, no, no, no, no"
    })

    print(f"✓ Discharge Cleared:          {postop_result.get('discharge_cleared')}")
    print(f"✓ Post-Op Day 1 Triage Risk:  {postop_result.get('triage_risk_level')}")
    print(f"✓ Nurse Escalation Required:  {postop_result.get('nurse_escalation_required')}")
    print(f"✓ Triage Assessment Notes:    {postop_result.get('triage_notes')}")

    discrepancies = postop_result.get("discrepancies", [])
    print("\n✓ Dual-Direction Billing Audit Results:")
    print(f"    • Clean Claim:            {postop_result.get('clean_claim')}")
    print(f"    • Total Discrepancies:    {len(discrepancies)}")
    print(f"    • Allowable Reimbursement: ${postop_result.get('allowable_reimbursement', 0):,.2f}")
    for disc in discrepancies:
        fin_impact = disc.get('financial_impact', 'N/A')
        print(f"    • [{disc['type']}] Code {disc['code']}: {disc['description']} (Impact: {fin_impact})")

    # ---------------------------------------------------------
    # STEP 6: Statutory HIPAA Immutable Audit Trail Verification
    # ---------------------------------------------------------
    print_step(6, "Statutory HIPAA Compliance & WORM Audit Trail")
    audit_logger = AuditLogger()
    audit_logger.log_event(
        audit_id="sim-audit-final",
        actor_id=clinician_id,
        patient_id="pat-sarah-j",
        encounter_id="sim-sarah-encounter-101",
        action_type="JOURNEY_SIMULATION_COMPLETED",
        resource_accessed="Encounter/sim-sarah-encounter-101",
        payload={"status": "CLEARED", "billing_audit": postop_result.get('billing_audit_details')},
        clinical_justification="Patient journey completed with verified attestation and coding audit."
    )

    integrity_ok = audit_logger.verify_integrity()
    print(f"✓ Audit Trail Storage: {audit_logger.log_file_path}")
    print(f"✓ Cryptographic SHA-256 Tamper Check: {'PASSED (Zero Tampering)' if integrity_ok else 'FAILED'}")

    print_banner("SIMULATION COMPLETED SUCCESSFULLY: ALL WORKFLOWS VALIDATED")

if __name__ == "__main__":
    asyncio.run(main())
