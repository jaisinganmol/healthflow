import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.infrastructure.security.signatures import SignatureService
from src.infrastructure.persistence.audit_logger import AuditLogger

@pytest.mark.asyncio
async def test_end_to_end_sarah_johnson_journey():
    transport = ASGITransport(app=app) # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        h_resp = await client.get("/health")
        assert h_resp.status_code == 200
        assert h_resp.json()["status"] == "HEALTHY"

        # 2. Pre-Admission Trigger (Sarah Johnson, CPT 27130 Total Hip)
        encounter_id = "enc-sarah-101"
        admit_resp = await client.post("/api/v1/events/admission", json={
            "patient_id": "pat-sarah-j",
            "encounter_id": encounter_id,
            "procedure_cpt": "27130",
            "surgeon_id": "dr-smith-ortho"
        })
        assert admit_resp.status_code == 200
        admit_data = admit_resp.json()
        assert admit_data["risk_tier"] == "TIER_2_REVIEWED"
        assert admit_data["status"] == "PAUSED_AT_CHECKPOINT"
        assert admit_data["scheduling_status"] == "COMPLETED"
        assert admit_data["insurance_status"] == "APPROVED"
        assert len(admit_data["flags"]) >= 4

        # 3. Clinician Key Registration & Cryptographic Sign-Off
        private_pem, public_pem = SignatureService.generate_key_pair()
        clinician_id = "dr-anesthesiologist-01"

        reg_resp = await client.post("/api/v1/cases/register-key", json={
            "clinician_id": clinician_id,
            "public_key_pem": public_pem
        })
        assert reg_resp.status_code == 200

        # Sign attestation
        decision = "APPROVED"
        notes = "Risk flags reviewed: Metformin hold confirmed, CKD 3a managed, Aspirin status noted. Cleared."
        sig = SignatureService.sign_attestation(private_pem, encounter_id, decision, notes)

        # Resume paused case
        resume_resp = await client.post(f"/api/v1/cases/{encounter_id}/resume", json={
            "clinician_id": clinician_id,
            "attestation_decision": decision,
            "clinical_notes": notes,
            "signature_base64": sig
        })
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "CLEARED"
        assert resume_resp.json()["clearance_committed_to_ehr"] is True

        # 4. Post-Discharge Day 1 Check-In (Normal Recovery: Pain 5, No red flags)
        dc_resp = await client.post("/api/v1/events/discharge", json={
            "patient_id": "pat-sarah-j",
            "encounter_id": encounter_id,
            "cpt_code": "27130",
            "pod_day": 1,
            "patient_sms_response": "5, no, no, no, no"
        })
        assert dc_resp.status_code == 200
        dc_data = dc_resp.json()
        assert dc_data["discharge_cleared"] is True
        assert dc_data["triage_risk_level"] == "LOW_RISK"
        assert dc_data["nurse_escalation_required"] is False
        # Billing discrepancy audit flagged omitted CKD 3a comorbidity
        assert dc_data["clean_claim"] is False
        assert any(d["code"] == "N18.30" for d in dc_data["discrepancies"])

        # 5. Inbound Twilio SMS Webhook
        sms_resp = await client.post(
            "/api/v1/sms/webhook",
            data={"From": "+15551234567", "Body": "B"}
        )
        assert sms_resp.status_code == 200
        assert "Slot option B has been confirmed" in sms_resp.text

        # 6. Verify Immutable Audit Log
        audit = AuditLogger()
        records = audit.read_records()
        assert len(records) >= 2
        assert audit.verify_integrity() is True
