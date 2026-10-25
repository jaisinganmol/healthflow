from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models.fhir import (
    FHIRPatient, FHIRCondition, FHIRObservation,
    FHIRMedicationStatement, FHIRAllergyIntolerance,
    FHIRProcedure, FHIRDocumentReference
)

class EHRClient(ABC):
    @abstractmethod
    async def get_patient(self, patient_id: str) -> FHIRPatient:
        """Fetch patient demographics and MRN."""
        pass

    @abstractmethod
    async def get_active_conditions(self, patient_id: str) -> List[FHIRCondition]:
        """Fetch active problem list / ICD-10 diagnoses."""
        pass

    @abstractmethod
    async def get_observations(self, patient_id: str, loinc_codes: Optional[List[str]] = None) -> List[FHIRObservation]:
        """Fetch finalized baseline lab panels and vitals."""
        pass

    @abstractmethod
    async def get_medication_statements(self, patient_id: str) -> List[FHIRMedicationStatement]:
        """Fetch active outpatient prescriptions."""
        pass

    @abstractmethod
    async def get_allergies(self, patient_id: str) -> List[FHIRAllergyIntolerance]:
        """Fetch documented allergies and intolerances."""
        pass

    @abstractmethod
    async def commit_clearance_status(
        self,
        patient_id: str,
        encounter_id: str,
        status: str,
        attestation_signature: Optional[str]
    ) -> bool:
        """Commit pre-op clearance approval or pause back to EHR."""
        pass
