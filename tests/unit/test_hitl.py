import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from src.infrastructure.security.signatures import SignatureService
from src.api.routes_hitl import router

app = FastAPI()
app.include_router(router)

def test_signature_generation_and_verification():
    private_pem, public_pem = SignatureService.generate_key_pair()
    case_id = "enc-sarah-101"
    decision = "APPROVED"
    notes = "Reviewed labs and risk flags. Proceed with total hip replacement."

    # 1. Sign
    sig = SignatureService.sign_attestation(private_pem, case_id, decision, notes)
    assert sig is not None

    # 2. Verify valid
    is_valid = SignatureService.verify_attestation(public_pem, case_id, decision, notes, sig)
    assert is_valid is True

    # 3. Verify tampering fails
    is_tampered = SignatureService.verify_attestation(public_pem, case_id, "REJECTED", notes, sig)
    assert is_tampered is False

@pytest.mark.asyncio
async def test_hitl_resume_api_flow():
    private_pem, public_pem = SignatureService.generate_key_pair()
    clinician_id = "dr-anesthesia-007"
    case_id = "enc-sarah-101"

    transport = ASGITransport(app=app) # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register key
        reg_resp = await client.post("/api/v1/cases/register-key", json={
            "clinician_id": clinician_id,
            "public_key_pem": public_pem
        })
        assert reg_resp.status_code == 200

        # 2. Get pending cases
        pending_resp = await client.get("/api/v1/cases/pending")
        assert pending_resp.status_code == 200
        cases = pending_resp.json()
        assert any(c["case_id"] == case_id for c in cases)

        # 3. Attempt resume with invalid signature -> 401
        bad_resume = await client.post(f"/api/v1/cases/{case_id}/resume", json={
            "clinician_id": clinician_id,
            "attestation_decision": "APPROVED",
            "clinical_notes": "All looks good.",
            "signature_base64": "invalid_base64_sig=="
        })
        assert bad_resume.status_code == 401

        # 4. Sign properly and resume -> 200
        decision = "APPROVED"
        notes = "Patient cleared for surgery under protocol."
        valid_sig = SignatureService.sign_attestation(private_pem, case_id, decision, notes)

        good_resume = await client.post(f"/api/v1/cases/{case_id}/resume", json={
            "clinician_id": clinician_id,
            "attestation_decision": decision,
            "clinical_notes": notes,
            "signature_base64": valid_sig
        })
        assert good_resume.status_code == 200
        data = good_resume.json()
        assert data["status"] == "CLEARED"
        assert data["clearance_committed_to_ehr"] is True
