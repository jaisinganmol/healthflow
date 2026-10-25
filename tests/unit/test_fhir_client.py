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

def test_raw_epic_fhir_r4_normalization():
    from src.domain.models.fhir import FHIRPatient, FHIRCondition, FHIRObservation, FHIRMedicationStatement

    # 1. Epic Patient Resource with arrays
    raw_epic_patient = {
        "resourceType": "Patient",
        "id": "Tbt3KuCDeD6u69JFaKkgugw3",
        "identifier": [
            {
                "use": "usual",
                "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
                "value": "E10001"
            }
        ],
        "name": [
            {
                "use": "official",
                "text": "Derrick Lin",
                "family": "Lin",
                "given": ["Derrick"]
            }
        ],
        "telecom": [
            {"system": "phone", "value": "+15559876543"}
        ],
        "gender": "male",
        "birthDate": "1973-05-12"
    }
    patient = FHIRPatient(**raw_epic_patient)
    assert patient.name == "Derrick Lin"
    assert patient.mrn == "E10001"
    assert patient.telecom_phone == "+15559876543"
    assert patient.gender == "male"
    assert patient.age > 40

    # 2. Epic Condition with CodeableConcept status
    raw_epic_condition = {
        "resourceType": "Condition",
        "id": "cond-epic-1",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
        },
        "code": {
            "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "E11.9", "display": "Type 2 diabetes"}],
            "text": "Type 2 diabetes"
        }
    }
    condition = FHIRCondition(**raw_epic_condition)
    assert condition.clinicalStatus == "active"
    assert condition.verificationStatus == "confirmed"

    # 3. Epic Observation with valueQuantity sub-object
    raw_epic_observation = {
        "resourceType": "Observation",
        "id": "obs-epic-1",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin"}],
            "text": "Hemoglobin"
        },
        "status": "final",
        "effectiveDateTime": "2024-01-10T10:00:00Z",
        "valueQuantity": {
            "value": 14.2,
            "unit": "g/dL"
        }
    }
    observation = FHIRObservation(**raw_epic_observation)
    assert observation.valueQuantity_value == 14.2
    assert observation.valueQuantity_unit == "g/dL"

    # 4. Epic MedicationRequest mapped to MedicationStatement
    raw_epic_medication = {
        "resourceType": "MedicationRequest",
        "id": "med-epic-1",
        "status": "active",
        "medicationCodeableConcept": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975", "display": "Metformin"}],
            "text": "Metformin 500mg"
        },
        "dosageInstruction": [{"text": "500 mg orally twice daily"}]
    }
    medication = FHIRMedicationStatement(**raw_epic_medication)
    assert medication.status == "active"
    assert medication.dosage_text == "500 mg orally twice daily"

@pytest.mark.asyncio
async def test_search_patients_mock():
    client = MockEHRClient()
    results = await client.search_patients(family="Johnson")
    assert len(results) == 1
    assert results[0].name == "Sarah Johnson"
