import pytest
from src.infrastructure.ehr.mock_client import MockEHRClient
from src.domain.models.fhir import FHIRObservation
from src.domain.exceptions import MissingClinicalDataException
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_mock_ehr_sarah_johnson_extraction():
    client = MockEHRClient()
    
    # 1. Patient demographics
    patient = await client.get_patient("pat-sarah-j")
    assert patient.name == "Sarah Johnson"
    assert patient.mrn == "MRN-984210"
    assert patient.age >= 67 # Born 1957
    assert patient.telecom_phone == "+15551234567"
    
    # 2. Conditions
    conditions = await client.get_active_conditions("pat-sarah-j")
    assert len(conditions) >= 4
    cond_codes = [c.code.coding[0].code for c in conditions if c.code.coding]
    assert "M17.11" in cond_codes # Osteoarthritis
    assert "N18.30" in cond_codes # CKD 3a
    
    # 3. Observations & Vitals
    obs = await client.get_observations("pat-sarah-j")
    assert len(obs) >= 5
    loinc_map = {o.code.coding[0].code: o.valueQuantity_value for o in obs if o.code.coding}
    assert loinc_map["718-7"] == 11.2  # Hemoglobin
    assert loinc_map["33914-3"] == 52.0 # eGFR
    assert loinc_map["2160-0"] == 1.4  # Creatinine
    assert loinc_map["4548-4"] == 7.2  # HbA1c
    assert loinc_map["49563-0"] == 0.02 # Troponin
    
    # 4. Medications
    meds = await client.get_medication_statements("pat-sarah-j")
    assert len(meds) >= 3
    med_names = [m.medicationCodeableConcept.text.lower() for m in meds if m.medicationCodeableConcept.text]
    assert any("metformin" in name for name in med_names)
    assert any("aspirin" in name for name in med_names)
    
    # 5. Allergies
    allergies = await client.get_allergies("pat-sarah-j")
    assert len(allergies) >= 1
    assert allergies[0].criticality == "high"

def test_missing_clinical_data_fail_closed():
    # Attempting to instantiate an Observation with missing numeric and string value must fail closed
    with pytest.raises(MissingClinicalDataException):
        FHIRObservation(
            id="obs-corrupt",
            code={"coding": [{"system": "http://loinc.org", "code": "718-7"}], "text": "Hemoglobin"},
            status="final",
            effectiveDateTime=datetime.now(timezone.utc),
            valueQuantity_value=None,
            valueString=None
        )
