import pytest
from src.domain.rules.clinical_gate import ClinicalGateEngine
from src.domain.models.clinical import RiskTier
from src.infrastructure.ehr.mock_client import MockEHRClient
from src.domain.models.fhir import FHIRPatient, FHIRCondition, FHIRObservation
from datetime import date, datetime

@pytest.mark.asyncio
async def test_sarah_johnson_tier_2_routing():
    ehr = MockEHRClient()
    patient = await ehr.get_patient("pat-sarah-j")
    conditions = await ehr.get_active_conditions("pat-sarah-j")
    labs = await ehr.get_observations("pat-sarah-j")
    meds = await ehr.get_medication_statements("pat-sarah-j")

    score, tier, flags, summary = ClinicalGateEngine.evaluate_case(
        patient=patient,
        conditions=conditions,
        labs=labs,
        meds=meds,
        cpt="27130"
    )

    # Assertions based on Sarah Johnson persona from specification:
    # Age 67, CKD 3a (severe systemic comorbidity) -> ASA 2 or 3
    # Major hip arthroplasty -> RCRI >= 1
    # Active flags: Anemia, CKD 3a, Metformin hold, Aspirin status, VTE
    assert tier == RiskTier.TIER_2_REVIEWED
    assert score >= 4.0
    flag_codes = [f.code for f in flags]
    assert "FLAG_1_MILD_ANEMIA" in flag_codes
    assert "FLAG_2_CKD_STAGE_3A" in flag_codes
    assert "FLAG_3_METFORMIN_PREOP_HOLD" in flag_codes
    assert "FLAG_4_ASPIRIN_BLEED_RISK" in flag_codes
    assert "FLAG_5_HIGH_VTE_PROTOCOL" in flag_codes

def test_healthy_young_patient_tier_1():
    young_patient = FHIRPatient(
        id="pat-healthy",
        mrn="MRN-001",
        name="Healthy Person",
        birthDate=date(1998, 5, 10), # Age ~28
        gender="male",
        telecom_phone="+15559998888"
    )
    # Minor procedure, no active conditions, normal labs, no meds
    score, tier, flags, summary = ClinicalGateEngine.evaluate_case(
        patient=young_patient,
        conditions=[],
        labs=[],
        meds=[],
        cpt="10060" # Simple incision & drainage
    )
    # No systemic disease, age < 65, RCRI 0 -> Tier 1 Automated
    assert tier == RiskTier.TIER_1_AUTO
    assert score <= 1.5
