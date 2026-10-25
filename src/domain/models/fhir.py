from datetime import date, datetime
from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
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

    @model_validator(mode="before")
    @classmethod
    def normalize_fhir_patient(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Normalize Name from FHIR R4 HumanName array
        if "name" in data and isinstance(data["name"], list) and len(data["name"]) > 0:
            first_name = data["name"][0]
            if isinstance(first_name, dict):
                full_name = first_name.get("text")
                if not full_name:
                    given = " ".join(first_name.get("given", []))
                    family = first_name.get("family", "")
                    full_name = f"{given} {family}".strip()
                data["name"] = full_name or "Unknown Patient"
        elif "name" not in data:
            data["name"] = "Unknown Patient"

        # Normalize MRN from FHIR R4 identifier array
        if "mrn" not in data or not data["mrn"]:
            mrn_val = None
            for ident in data.get("identifier", []):
                if isinstance(ident, dict):
                    type_obj = ident.get("type", {})
                    type_codes = [c.get("code") for c in type_obj.get("coding", []) if isinstance(c, dict)]
                    if "MR" in type_codes:
                        mrn_val = ident.get("value")
                        break
                    if not mrn_val:
                        mrn_val = ident.get("value")
            data["mrn"] = mrn_val or f"MRN-{data.get('id', 'UNKNOWN')}"

        # Normalize Phone from FHIR R4 telecom array
        if "telecom_phone" not in data or not data["telecom_phone"]:
            phone_val = None
            for contact in data.get("telecom", []):
                if isinstance(contact, dict) and contact.get("system") == "phone":
                    phone_val = contact.get("value")
                    break
            data["telecom_phone"] = phone_val or "+15550000000"

        # Normalize Gender fallback
        if "gender" in data and data["gender"] not in ["male", "female", "other", "unknown"]:
            data["gender"] = "unknown"

        return data

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

    @model_validator(mode="before")
    @classmethod
    def normalize_fhir_condition(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Normalize clinicalStatus CodeableConcept to literal string
        if isinstance(data.get("clinicalStatus"), dict):
            coding = data["clinicalStatus"].get("coding", [])
            data["clinicalStatus"] = coding[0].get("code", "active") if coding else "active"

        # Normalize verificationStatus CodeableConcept to literal string
        if isinstance(data.get("verificationStatus"), dict):
            coding = data["verificationStatus"].get("coding", [])
            data["verificationStatus"] = coding[0].get("code", "confirmed") if coding else "confirmed"

        return data

class FHIRObservation(BaseModel):
    resourceType: Literal["Observation"] = "Observation"
    id: str
    code: FHIRCodeableConcept
    status: Literal["final", "amended", "preliminary"]
    effectiveDateTime: datetime
    valueQuantity_value: Optional[float] = None
    valueQuantity_unit: Optional[str] = None
    valueString: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fhir_observation(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Extract valueQuantity sub-object in standard FHIR R4
        if "valueQuantity" in data and isinstance(data["valueQuantity"], dict):
            if "valueQuantity_value" not in data or data["valueQuantity_value"] is None:
                data["valueQuantity_value"] = data["valueQuantity"].get("value")
            if "valueQuantity_unit" not in data or data["valueQuantity_unit"] is None:
                data["valueQuantity_unit"] = data["valueQuantity"].get("unit")

        return data

    @field_validator("valueQuantity_value")
    @classmethod
    def validate_has_value(cls, v: Optional[float], info) -> Optional[float]:
        # Finalized observations must have a valid value or explicitly fail-closed
        if v is None and not (info.data.get("valueString") if hasattr(info, 'data') else None):
            raise MissingClinicalDataException("Finalized Observation missing clinical numeric or string value")
        return v

class FHIRMedicationStatement(BaseModel):
    resourceType: Literal["MedicationStatement", "MedicationRequest"] = "MedicationStatement"
    id: str
    medicationCodeableConcept: FHIRCodeableConcept
    status: Literal["active", "completed", "entered-in-error", "intended", "stopped", "on-hold"]
    effectiveDateTime: Optional[datetime] = None
    dosage_text: str

    @model_validator(mode="before")
    @classmethod
    def normalize_fhir_medication(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Support MedicationRequest from Epic
        if data.get("resourceType") == "MedicationRequest":
            data["resourceType"] = "MedicationStatement"

        if "dosage_text" not in data or not data["dosage_text"]:
            dosage_inst = data.get("dosageInstruction", [])
            if dosage_inst and isinstance(dosage_inst[0], dict):
                data["dosage_text"] = dosage_inst[0].get("text") or "Prescribed dosage"
            else:
                data["dosage_text"] = "Prescribed dosage"

        return data

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
