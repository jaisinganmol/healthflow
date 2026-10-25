import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.domain.models.fhir import (
    FHIRPatient, FHIRCondition, FHIRObservation,
    FHIRMedicationStatement, FHIRAllergyIntolerance,
    FHIRProcedure, FHIRDocumentReference
)
from src.infrastructure.ehr.base import EHRClient
from src.domain.exceptions import MissingClinicalDataException

class MockEHRClient(EHRClient):
    """
    Mock EHR client reading from Synthea FHIR R4 JSON bundles.
    Used for local execution, deterministic CI testing, and evaluation runs.
    """
    def __init__(self, bundle_path: Optional[Path] = None):
        if bundle_path is None:
            bundle_path = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "synthea" / "sarah_johnson.json"
        self.bundle_path = bundle_path
        self._load_bundle()

    def _load_bundle(self) -> None:
        with open(self.bundle_path, "r", encoding="utf-8") as f:
            self._raw = json.load(f)

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        for entry in self._raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Patient":
                return FHIRPatient(**res)
        raise MissingClinicalDataException(f"Patient {patient_id} not found in bundle")

    async def search_patients(
        self,
        family: Optional[str] = None,
        given: Optional[str] = None,
        patient_ids: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[FHIRPatient]:
        patients = []
        for entry in self._raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Patient":
                p = FHIRPatient(**res)
                if patient_ids and p.id not in patient_ids:
                    continue
                if family and family.lower() not in p.name.lower():
                    continue
                if given and given.lower() not in p.name.lower():
                    continue
                patients.append(p)
                if len(patients) >= limit:
                    break
        return patients

    async def get_active_conditions(self, patient_id: str) -> List[FHIRCondition]:
        conditions = []
        for entry in self._raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Condition":
                conditions.append(FHIRCondition(**res))
        return conditions

    async def get_observations(self, patient_id: str, loinc_codes: Optional[List[str]] = None) -> List[FHIRObservation]:
        observations = []
        for entry in self._raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Observation":
                observations.append(FHIRObservation(**res))
        return observations

    async def get_medication_statements(self, patient_id: str) -> List[FHIRMedicationStatement]:
        meds = []
        for entry in self._raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "MedicationStatement":
                meds.append(FHIRMedicationStatement(**res))
        return meds

    async def get_allergies(self, patient_id: str) -> List[FHIRAllergyIntolerance]:
        allergies = []
        for entry in self._raw.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "AllergyIntolerance":
                allergies.append(FHIRAllergyIntolerance(**res))
        return allergies

    async def commit_clearance_status(
        self,
        patient_id: str,
        encounter_id: str,
        status: str,
        attestation_signature: Optional[str]
    ) -> bool:
        # Simulates committing clearance attestation back to EHR chart
        return True
