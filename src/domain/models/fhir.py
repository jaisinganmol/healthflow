from datetime import date, datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from src.domain.exceptions import MissingClinicalDataException

class FHIRCoding(BaseModel):
    system: str
    code: str
    display: Optional[str] = None

class FHIRCodeableConcept(BaseModel):
    coding: List[FHIRCoding] = Field(default_factory=list)
    text: Optional[str] = None

class FHIRPatient(BaseModel):
    resourceType: Literal["Patient"] = "Patient"
    id: str
    mrn: str
    name: str
    birthDate: date
    gender: Literal["male", "female", "other", "unknown"]
    telecom_phone: str

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.birthDate.year - (
            (today.month, today.day) < (self.birthDate.month, self.birthDate.day)
        )

class FHIRCondition(BaseModel):
    resourceType: Literal["Condition"] = "Condition"
    id: str
    code: FHIRCodeableConcept
    clinicalStatus: Literal["active", "recurrence", "relapse", "inactive", "remission", "resolved"]
    verificationStatus: Literal["confirmed", "provisional", "differential", "refuted"]
    onsetDateTime: Optional[datetime] = None

class FHIRObservation(BaseModel):
    resourceType: Literal["Observation"] = "Observation"
    id: str
    code: FHIRCodeableConcept
    status: Literal["final", "amended", "preliminary"]
    effectiveDateTime: datetime
    valueQuantity_value: Optional[float] = None
    valueQuantity_unit: Optional[str] = None
    valueString: Optional[str] = None

    @field_validator("valueQuantity_value")
    @classmethod
    def validate_has_value(cls, v: Optional[float], info) -> Optional[float]:
        # Finalized observations must have a valid value or explicitly fail-closed
        if v is None and not (info.data.get("valueString") if hasattr(info, 'data') else None):
            raise MissingClinicalDataException("Finalized Observation missing clinical numeric or string value")
        return v

class FHIRMedicationStatement(BaseModel):
    resourceType: Literal["MedicationStatement"] = "MedicationStatement"
    id: str
    medicationCodeableConcept: FHIRCodeableConcept
    status: Literal["active", "completed", "entered-in-error", "intended", "stopped", "on-hold"]
    effectiveDateTime: Optional[datetime] = None
    dosage_text: str

class FHIRAllergyIntolerance(BaseModel):
    resourceType: Literal["AllergyIntolerance"] = "AllergyIntolerance"
    id: str
    code: FHIRCodeableConcept
    criticality: Optional[Literal["low", "high", "unable-to-assess"]] = None
    type: Optional[Literal["allergy", "intolerance"]] = None
    reaction_manifestation: List[str] = Field(default_factory=list)

class FHIRProcedure(BaseModel):
    resourceType: Literal["Procedure"] = "Procedure"
    id: str
    code: FHIRCodeableConcept # CPT or SNOMED
    status: Literal["preparation", "in-progress", "not-done", "on-hold", "stopped", "completed"]
    performedDateTime: Optional[datetime] = None

class FHIRDocumentReference(BaseModel):
    resourceType: Literal["DocumentReference"] = "DocumentReference"
    id: str
    type: FHIRCodeableConcept
    docStatus: Literal["preliminary", "final", "amended"]
    content_text: Optional[str] = None
    content_url: Optional[str] = None
