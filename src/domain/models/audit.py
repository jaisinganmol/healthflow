from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib
import json

class AuditRecord(BaseModel):
    audit_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: str
    patient_id: str
    encounter_id: str
    action_type: str
    resource_accessed: str
    payload_hash: str
    clinical_justification: str
    attestation_signature: Optional[str] = None

    @classmethod
    def generate(
        cls,
        audit_id: str,
        actor_id: str,
        patient_id: str,
        encounter_id: str,
        action_type: str,
        resource_accessed: str,
        payload: Dict[str, Any],
        clinical_justification: str,
        signature: Optional[str] = None
    ) -> "AuditRecord":
        serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        p_hash = hashlib.sha256(serialized).hexdigest()
        return cls(
            audit_id=audit_id,
            actor_id=actor_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            action_type=action_type,
            resource_accessed=resource_accessed,
            payload_hash=p_hash,
            clinical_justification=clinical_justification,
            attestation_signature=signature
        )
